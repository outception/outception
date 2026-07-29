// Usage: node send-push.js <payload-name>   (names are the keys in push-payload.js)
const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')
const TEMP_FILE = path.join(__dirname, '.push-payload-temp.json')
const payloads = require('./push-payload')
const BUNDLE_ID = 'com.outception.Outception'

const name = process.argv[2]
const payload = name && payloads[name]
if (!payload) {
  console.error(
    name ? `Unknown payload: "${name}"` : 'Usage: send-push.js <payload-name>',
  )
  console.error(`Available: ${Object.keys(payloads).join(', ')}`)
  process.exit(1)
}

try {
  fs.writeFileSync(TEMP_FILE, JSON.stringify(payload, null, 2))
  console.log(`Sending "${name}" to the booted iOS simulator...`)
  execSync(`xcrun simctl push booted "${BUNDLE_ID}" "${TEMP_FILE}"`, {
    stdio: 'inherit',
  })
} catch (error) {
  console.error(`Failed: ${error.message}`)
  process.exit(1)
} finally {
  if (fs.existsSync(TEMP_FILE)) {
    fs.unlinkSync(TEMP_FILE)
  }
}
