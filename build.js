const fs = require("node:fs/promises");
const path = require("path");

const djot = require("@djot/djot");

class FileCache {
  constructor() {
    this.cache = {};
  }

  async readFile(filePath) {
    const cachedFile = this.cache[filePath];
    if (cachedFile) {
      return cachedFile;
    }

    try {
      const data = await fs.readFile(filePath, "utf8");
      this.cache[filePath] = data;
      return data;
    } catch (error) {
      console.error(`Error reading file ${filePath}: ${error.message}`);
      throw error;
    }
  }
}
const fileCache = new FileCache();

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

function getBasename(path) {
  return path.split("/").pop().split(".").shift();
}

function toTitleCase(str) {
  return str
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

async function writeDjotToHtml(filePath) {
  if (!filePath.endsWith(".dj")) return;

  const baseName = getBasename(filePath);
  if (baseName.startsWith("_")) {
    console.debug(`Skipping '_' prefixed page: ${filePath}`);
    await fs.unlink(filePath);
    return;
  }

  var header = await fileCache.readFile("templates/header.html");
  header = header.replace("{TITLE}", `Recipe: ${toTitleCase(baseName)}`);
  const footer = await fileCache.readFile("templates/footer.html");

  try {
    const text = await fs.readFile(filePath, "utf8");
    var section = djot.renderHTML(djot.parse(text));
    if (!filePath.endsWith("index.dj")) {
      section = `<main data-pagefind-body>${section}</main>`;
    }
    const html = `${header}\n${section}\n${footer}`;

    await fs.writeFile(filePath.replace(".dj", ".html"), html);
  } catch (error) {
    console.error(`Error converting to HTML ${filePath}: ${error.message}`);
    throw error;
  }

  await fs.unlink(filePath);
}

async function renDir() {
  try {
    await traverseDirectory({
      directory: `${process.cwd()}/public`,
      fileCb: writeDjotToHtml,
    });
  } catch (error) {
    console.error("Error traversing directory:", error);
  }
}

renDir();
