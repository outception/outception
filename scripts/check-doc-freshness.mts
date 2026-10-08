// Specs carry two markers:
//
//   <!-- doc-covers: path other/path -->
//   <!-- doc-verified: <commit> -->
//
// A doc is fresh while nothing under its covered paths changed since it
// was last verified: the marker's commit, or the doc's own last commit when
// that is later (a doc edited beside the code it covers was read against
// it). --check fails on a stale doc; without it the stale docs are listed.
// Re-verify by reading the doc against the code and moving the marker.
// Runs under Node 24 with native type stripping:
//
//   node scripts/check-doc-freshness.mts [--check]

import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const check = process.argv.includes("--check");

const git = (...args: string[]): string =>
  execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();

const isAncestor = (older: string, newer: string): boolean => {
  try {
    git("merge-base", "--is-ancestor", older, newer);
    return true;
  } catch {
    return false;
  }
};

const docs = (dir: string, out: string[] = []): string[] => {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name.startsWith(".")) continue;
    const full = join(dir, name);
    if (statSync(full).isDirectory()) docs(full, out);
    else if (name.endsWith(".md")) out.push(full);
  }
  return out;
};

interface Spec {
  file: string;
  covers: string[];
  verified: string;
}

const specs: Spec[] = [];
for (const file of [
  ...docs(join(root, "docs")),
  ...docs(root).filter((f) => !f.includes("/docs/")),
]) {
  const text = readFileSync(file, "utf8");
  const covers = /<!--\s*doc-covers:\s*([^>]+?)\s*-->/.exec(text);
  const verified = /<!--\s*doc-verified:\s*([0-9a-f]{7,40})\s*-->/.exec(text);
  if (!covers || !verified) continue;
  specs.push({
    file: relative(root, file),
    covers: covers[1]!.split(/\s+/).filter(Boolean),
    verified: verified[1]!,
  });
}

let stale = 0;
for (const spec of specs) {
  let changed: string[];
  try {
    git("cat-file", "-e", `${spec.verified}^{commit}`);
    // A commit kept only on a local branch from before a fresh root is
    // outside this history, the same as one the clone does not have.
    if (!isAncestor(spec.verified, "HEAD")) throw new Error("not in this history");
    // The later of the marker and the doc's own last commit.
    const docCommit = git("log", "-1", "--format=%H", "--", spec.file);
    const since = docCommit && isAncestor(spec.verified, docCommit) ? docCommit : spec.verified;
    // Against the working tree, not HEAD: a doc has to be bumped in the
    // same change that touches what it covers, before the commit. A doc
    // with uncommitted edits of its own is being brought up to date.
    const editing = git("diff", "--name-only", "--", spec.file) !== "";
    changed = editing
      ? ""
      : git("diff", "--name-only", since, "--", ...spec.covers)
          .split("\n")
          .filter(Boolean);
  } catch {
    // The marker names a commit outside this history: the history was
    // replaced by a fresh root since the doc was verified. Everything in
    // that root was verified then, so the root is the point to diff from.
    const root = git("rev-list", "--max-parents=0", "HEAD").split("\n")[0];
    const editing = git("diff", "--name-only", "--", spec.file) !== "";
    changed = editing
      ? []
      : git("diff", "--name-only", root, "--", ...spec.covers)
          .split("\n")
          .filter(Boolean);
    if (changed.length > 0) {
      console.log(`${spec.file}: stale since the fresh root; changed: ${changed.join(", ")}`);
      stale += 1;
    } else {
      console.log(`${spec.file}: fresh (verified before the fresh root)`);
    }
    continue;
  }
  if (changed.length === 0) {
    console.log(`${spec.file}: fresh (${spec.verified})`);
  } else {
    stale += 1;
    console.log(
      `${spec.file}: stale since ${spec.verified}; changed: ${changed.slice(0, 6).join(", ")}${changed.length > 6 ? ", ..." : ""}`,
    );
  }
}
console.log(`${specs.length} spec(s), ${stale} stale`);
if (check && stale > 0) process.exit(1);
