'use client'

import { useEffect, useRef } from 'react'

// Seconds per full drift cycle is governed by this — the lower the number, the
// slower the gradient flows. This is the speed control the library renderer
// never gave us; tweak freely.
const SPEED = 0.05

// Up to 5 palette colours feed the shader (padded if fewer are supplied).
const MAX_COLORS = 5

const VERT = `#version 300 es
in vec2 a_pos;
void main() {
  gl_Position = vec4(a_pos, 0.0, 1.0);
}`

// Soft "metaball" blend: each palette colour rides a slow Lissajous path; every
// pixel is a distance-weighted average of those colours. The result is a smooth,
// organic, continuously-morphing warm gradient — the same family of look as the
// blurred-gradient renderer, but with the flow speed fully under our control.
const FRAG = `#version 300 es
precision highp float;
uniform vec2 u_res;
uniform float u_time;
uniform vec3 u_colors[${MAX_COLORS}];
uniform int u_count;
out vec4 outColor;

void main() {
  float aspect = u_res.x / max(u_res.y, 1.0);
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p = vec2(uv.x * aspect, uv.y);
  float t = u_time;

  vec3 col = vec3(0.0);
  float wsum = 0.0;
  for (int i = 0; i < ${MAX_COLORS}; i++) {
    if (i >= u_count) break;
    float fi = float(i);
    vec2 c = vec2(
      aspect * (0.5 + 0.34 * sin(t * 0.6 + fi * 1.9)),
      0.5 + 0.34 * cos(t * 0.47 + fi * 2.4)
    );
    float d = distance(p, c);
    float w = 1.0 / (d * d * 5.0 + 0.10);
    col += u_colors[i] * w;
    wsum += w;
  }
  col /= max(wsum, 1e-4);
  outColor = vec4(col, 1.0);
}`

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  const full =
    h.length === 3
      ? h
          .split('')
          .map((c) => c + c)
          .join('')
      : h
  const v = parseInt(full, 16)
  return [((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255]
}

function compile(
  gl: WebGL2RenderingContext,
  type: number,
  src: string,
): WebGLShader | null {
  const shader = gl.createShader(type)
  if (!shader) return null
  gl.shaderSource(shader, src)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader)
    return null
  }
  return shader
}

/** Renders the Spectra background — a soft, slowly-flowing warm gradient — with
 * a small WebGL shader we own, so the flow speed is a constant (SPEED) we
 * control rather than the library's hard-coded pace. alpha:true so the CSS
 * fallback shows through until the first frame paints (no flash). */
export default function SpectraCanvas({ colors }: { colors: string[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      antialias: false,
      premultipliedAlpha: false,
    })
    if (!gl) return

    const vert = compile(gl, gl.VERTEX_SHADER, VERT)
    const frag = compile(gl, gl.FRAGMENT_SHADER, FRAG)
    const program = gl.createProgram()
    if (!vert || !frag || !program) return
    gl.attachShader(program, vert)
    gl.attachShader(program, frag)
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return
    gl.useProgram(program)

    // Fullscreen triangle.
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]),
      gl.STATIC_DRAW,
    )
    const posLoc = gl.getAttribLocation(program, 'a_pos')
    gl.enableVertexAttribArray(posLoc)
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0)

    // Static uniforms: the palette (padded to MAX_COLORS) + its real length.
    const rgb = colors.slice(0, MAX_COLORS).map(hexToRgb)
    const count = rgb.length
    const flat = new Float32Array(MAX_COLORS * 3)
    for (let i = 0; i < MAX_COLORS; i++) {
      const c = rgb[i] ?? rgb[count - 1] ?? [0, 0, 0]
      flat.set(c, i * 3)
    }
    gl.uniform3fv(gl.getUniformLocation(program, 'u_colors'), flat)
    gl.uniform1i(gl.getUniformLocation(program, 'u_count'), count)

    const uTime = gl.getUniformLocation(program, 'u_time')
    const uRes = gl.getUniformLocation(program, 'u_res')

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = Math.max(1, Math.floor(canvas.clientWidth * dpr))
      const h = Math.max(1, Math.floor(canvas.clientHeight * dpr))
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w
        canvas.height = h
      }
      gl.viewport(0, 0, canvas.width, canvas.height)
    }

    const drawAt = (time: number) => {
      resize()
      gl.uniform1f(uTime, time)
      gl.uniform2f(uRes, canvas.width, canvas.height)
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }

    // Honour prefers-reduced-motion: paint a single static frame (the warm
    // gradient is still there) and skip the drift loop entirely.
    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches
    if (reduceMotion) {
      drawAt(0)
      const onResize = () => drawAt(0)
      window.addEventListener('resize', onResize)
      return () => {
        window.removeEventListener('resize', onResize)
        gl.deleteProgram(program)
        gl.deleteShader(vert)
        gl.deleteShader(frag)
        gl.deleteBuffer(buffer)
      }
    }

    let raf = 0
    let startTime: number | null = null
    const render = (now: number) => {
      if (startTime === null) startTime = now
      // Our own clock: elapsed seconds × SPEED. Slow because SPEED is small.
      drawAt(((now - startTime) / 1000) * SPEED * Math.PI * 2)
      raf = requestAnimationFrame(render)
    }
    raf = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(raf)
      gl.deleteProgram(program)
      gl.deleteShader(vert)
      gl.deleteShader(frag)
      gl.deleteBuffer(buffer)
    }
  }, [colors])

  return <canvas ref={canvasRef} className="block h-full w-full" />
}
