const fs = require("node:fs/promises");
const path = require("path");

const djot = require("@djot/djot");

async function writeDjotToHtml(filePath) {
  if (!filePath.endsWith(".dj")) return;

  const text = await fs.readFile(filePath, "utf8");
  const html = djot.renderHTML(djot.parse(text));
  await fs.writeFile(filePath.replace(".dj", ".html"), html);
  await fs.unlink(filePath);
}

async function traverseDirectory(opts) {
  const directory = opts.directory;
  const fileCb = opts.fileCb;
  if (typeof fileCb === "undefined") throw Error("Error in parameters");

  const paths = await fs.readdir(directory);
  for (const name of paths) {
    const pth = path.join(directory, name);
    const stats = await fs.stat(pth);
    if (stats.isDirectory()) {
      await traverseDirectory({ directory: pth, fileCb: fileCb });
    } else if (stats.isFile()) {
      await fileCb(pth);
    }
  }
}

const DIR = "public";

try {
  traverseDirectory({
    directory: `${process.cwd()}/${DIR}`,
    fileCb: writeDjotToHtml,
  });
} catch (error) {
  console.error("Error traversing directory:", error);
}
