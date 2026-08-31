(() => {
	var REPO = "KyleKing/recipes";
	var API = "https://api.github.com";
	var BASE_BRANCH = "main";
	var TOKEN_KEY = "recipe-github-token";
	var TOKEN_HELP = "https://github.com/settings/personal-access-tokens/new";
	var PHOTO_MAX_HEIGHT = 900;
	var PHOTO_QUALITY = 0.85;

	var openPr = null;

	function sourcePath() {
		return `content${window.location.pathname.replace(/\.html$/, ".dj")}`;
	}

	function branchName() {
		return `edit/${sourcePath()
			.replace(/^content\//, "")
			.replace(/\.dj$/, "")
			.replace(/\//g, "-")}`;
	}

	function readToken() {
		try {
			return localStorage.getItem(TOKEN_KEY) || "";
		} catch (_e) {
			return "";
		}
	}

	function writeToken(token) {
		try {
			if (token) localStorage.setItem(TOKEN_KEY, token);
			else localStorage.removeItem(TOKEN_KEY);
		} catch (_e) {
			// Storage unavailable
		}
	}

	function encodeBase64(text) {
		var bytes = new TextEncoder().encode(text);
		var binary = "";
		bytes.forEach((b) => {
			binary += String.fromCharCode(b);
		});
		return btoa(binary);
	}

	function decodeBase64(encoded) {
		var binary = atob(encoded.replace(/\s/g, ""));
		var bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
		return new TextDecoder().decode(bytes);
	}

	function bytesToBase64(buffer) {
		var binary = "";
		new Uint8Array(buffer).forEach((b) => {
			binary += String.fromCharCode(b);
		});
		return btoa(binary);
	}

	// GitHub reports failures in the body, so surface that rather than a bare status code
	async function api(path, options) {
		var response = await fetch(API + path, {
			...options,
			headers: {
				Accept: "application/vnd.github+json",
				Authorization: `Bearer ${readToken()}`,
				...(options?.headers || {}),
			},
		});
		if (response.status === 404) return null;
		var body = await response.json().catch(() => null);
		if (!response.ok) {
			throw new Error(body?.message || `GitHub returned ${response.status}`);
		}
		return body;
	}

	async function branchExists(branch) {
		return Boolean(await api(`/repos/${REPO}/git/ref/heads/${branch}`));
	}

	async function ensureBranch() {
		var branch = branchName();
		if (await branchExists(branch)) return branch;

		var base = await api(`/repos/${REPO}/git/ref/heads/${BASE_BRANCH}`);
		if (!base) throw new Error(`${BASE_BRANCH} not found in ${REPO}`);
		await api(`/repos/${REPO}/git/refs`, {
			method: "POST",
			body: JSON.stringify({ ref: `refs/heads/${branch}`, sha: base.object.sha }),
		});
		return branch;
	}

	async function readFile(path, branch) {
		return api(`/repos/${REPO}/contents/${path}?ref=${branch}`);
	}

	async function readSource(branch) {
		var file = await readFile(sourcePath(), branch);
		return file ? { text: decodeBase64(file.content), sha: file.sha } : null;
	}

	async function commitFile(path, branch, contentBase64, sha, message) {
		var payload = { message: message, content: contentBase64, branch: branch };
		if (sha) payload.sha = sha;
		await api(`/repos/${REPO}/contents/${path}`, { method: "PUT", body: JSON.stringify(payload) });
	}

	// One open pull request per recipe, matched on its branch rather than its title so
	// rewording the title never orphans the edits
	async function findOpenPr() {
		var branch = branchName();
		var pulls = await api(`/repos/${REPO}/pulls?state=open&per_page=100`);
		return (pulls || []).find((pr) => pr.head?.ref === branch) || null;
	}

	async function ensurePr(branch, title) {
		var existing = await findOpenPr();
		if (existing) return existing;
		return api(`/repos/${REPO}/pulls`, {
			method: "POST",
			body: JSON.stringify({
				title: title,
				head: branch,
				base: BASE_BRANCH,
				body: `Edited from ${window.location.pathname} while cooking.`,
			}),
		});
	}

	function recipeTitle() {
		return document.querySelector("h1")?.textContent.trim() || sourcePath();
	}

	function imageBasename() {
		return sourcePath().split("/").pop().replace(/\.dj$/, "");
	}

	function replaceMetadata(source, key, value) {
		var pattern = new RegExp(`(${key}=")[^"]*(")`);
		if (!pattern.test(source)) {
			throw new Error(`No ${key} in ${sourcePath()} to edit`);
		}
		return source.replace(pattern, `$1${value}$2`);
	}

	// Reduce a source line to the words the page renders, so a changed line can be matched
	// against the row showing it
	function plainText(line) {
		return line
			.replace(/^\s*(?:[-*+]|\d+[.)])\s+/, "")
			.replace(/^\[[ xX]\]\s*/, "")
			.replace(/^#+\s+/, "")
			.replace(/\[([^\]]*)\]\{[^}]*\}/g, "$1")
			.replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
			.replace(/\s+/g, " ")
			.trim();
	}

	// Longest common subsequence over lines. Recipes run to tens of lines, so the quadratic
	// table costs nothing and reordering, indentation, and insertions all fall out of it.
	function diffLines(before, after) {
		var table = [];
		for (var row = 0; row <= before.length; row++) table.push(new Array(after.length + 1).fill(0));
		for (var i = before.length - 1; i >= 0; i--) {
			for (var j = after.length - 1; j >= 0; j--) {
				table[i][j] =
					before[i] === after[j]
						? table[i + 1][j + 1] + 1
						: Math.max(table[i + 1][j], table[i][j + 1]);
			}
		}

		var ops = [];
		var x = 0;
		var y = 0;
		while (x < before.length && y < after.length) {
			if (before[x] === after[y]) {
				ops.push({ type: "same", text: before[x] });
				x++;
				y++;
			} else if (table[x + 1][y] >= table[x][y + 1]) {
				ops.push({ type: "del", text: before[x] });
				x++;
			} else {
				ops.push({ type: "add", text: after[y] });
				y++;
			}
		}
		while (x < before.length) ops.push({ type: "del", text: before[x++] });
		while (y < after.length) ops.push({ type: "add", text: after[y++] });
		return ops;
	}

	function splitLines(text) {
		return text.replace(/\n$/, "").split("\n");
	}

	function changedOps(ops) {
		return ops.filter((op) => op.type !== "same");
	}

	// ----- Pending changes marked up on the rendered recipe -----

	// Rows are matched by their rendered words, consumed in document order so a recipe that
	// repeats a line still annotates the right one
	function rowIndex() {
		var index = new Map();
		document.querySelectorAll(".recipe-row").forEach((li) => {
			var label = li.querySelector(":scope > .item-label");
			if (!label) return;
			var key = label.textContent.replace(/\s+/g, " ").trim();
			if (!index.has(key)) index.set(key, []);
			index.get(key).push(li);
		});
		return index;
	}

	function takeRow(index, text) {
		var rows = index.get(text);
		return rows && rows.length > 0 ? rows.shift() : null;
	}

	function pendingLine(text) {
		var line = document.createElement("li");
		line.className = "pending-added";
		line.textContent = text;
		return line;
	}

	function clearPending() {
		document.querySelectorAll(".pending-added").forEach((el) => {
			el.remove();
		});
		document.querySelectorAll(".pending-removed").forEach((el) => {
			el.classList.remove("pending-removed");
		});
	}

	// Walk the diff in order, anchoring each change to the last row it could be placed
	// against. A change with no row to hang on (metadata, prose outside a list, an
	// indentation-only edit) is counted for the banner instead of being shown twice.
	function markPending(ops) {
		clearPending();
		var index = rowIndex();
		var anchor = null;
		var unplaced = 0;

		// `tail` trails `anchor` so a run of added lines keeps its order instead of each one
		// landing directly under the row and reversing the run
		var tail = null;

		ops.forEach((op) => {
			var text = plainText(op.text);
			if (op.type !== "add") {
				var row = takeRow(index, text);
				if (!row) {
					if (op.type === "del") unplaced++;
					return;
				}
				if (op.type === "del") row.classList.add("pending-removed");
				anchor = row;
				tail = row;
				return;
			}
			if (!text || !anchor || text === anchorText(anchor)) {
				unplaced++;
				return;
			}
			var line = pendingLine(text);
			tail.after(line);
			tail = line;
		});
		return unplaced;
	}

	function anchorText(row) {
		var label = row.querySelector(":scope > .item-label");
		return label ? label.textContent.replace(/\s+/g, " ").trim() : "";
	}

	async function showPending() {
		if (!openPr) return 0;
		var base = await readSource(BASE_BRANCH);
		var head = await readSource(openPr.head.ref);
		if (!base || !head || base.text === head.text) return 0;
		return markPending(diffLines(splitLines(base.text), splitLines(head.text)));
	}

	function showPrBanner(unplaced) {
		var banner = document.getElementById("edit-banner");
		if (!openPr) {
			banner?.remove();
			return;
		}
		if (!banner) {
			banner = document.createElement("p");
			banner.id = "edit-banner";
			banner.className = "edit-banner";
			document.querySelector("main")?.prepend(banner);
		}
		banner.textContent = "";
		var link = document.createElement("a");
		link.href = openPr.html_url;
		link.textContent = `Edits in progress: pull request #${openPr.number}`;
		banner.appendChild(link);
		if (unplaced > 0) {
			banner.append(
				` (${unplaced} more changed line${unplaced === 1 ? "" : "s"} only in the diff)`,
			);
		}
	}

	// ----- The editor -----

	async function saveEdits(text, sha, photo, report) {
		report("Preparing the branch…");
		var branch = await ensureBranch();

		if (photo) {
			report("Resizing the photo…");
			var photoName = `${imageBasename()}.jpeg`;
			var photoPath = sourcePath().replace(/[^/]+$/, photoName);
			var encoded = await shrinkPhoto(photo);
			var existing = await readFile(photoPath, branch);
			report("Uploading the photo…");
			await commitFile(
				photoPath,
				branch,
				encoded,
				existing?.sha,
				`feat(recipe): add a photo of ${recipeTitle()}`,
			);
			text = replaceMetadata(text, "image", photoName);
		}

		var commitMsg = `feat(recipe): ${recipeTitle()}`;
		report("Committing…");
		await commitFile(sourcePath(), branch, encodeBase64(text), sha, commitMsg);

		report("Opening the pull request…");
		openPr = await ensurePr(branch, commitMsg);
		return openPr;
	}

	// A canvas re-encode carries no metadata, so GPS never leaves the device. Decoding with
	// `from-image` applies the EXIF rotation, without which phone photos upload sideways.
	async function shrinkPhoto(file) {
		var bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
		var scale = Math.min(1, PHOTO_MAX_HEIGHT / bitmap.height);
		var canvas = document.createElement("canvas");
		canvas.width = Math.round(bitmap.width * scale);
		canvas.height = Math.round(bitmap.height * scale);
		canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
		bitmap.close();

		var blob = await new Promise((resolve) => {
			canvas.toBlob(resolve, "image/jpeg", PHOTO_QUALITY);
		});
		if (!blob) throw new Error("Could not re-encode the photo");
		return bytesToBase64(await blob.arrayBuffer());
	}

	function renderTokenForm(body, refresh) {
		var input = document.createElement("input");
		input.type = "password";
		input.id = "edit-token";
		input.className = "edit-input";
		input.autocomplete = "off";
		input.placeholder = "github_pat_…";
		body.appendChild(input);

		var help = document.createElement("p");
		help.className = "edit-help";
		var link = document.createElement("a");
		link.href = TOKEN_HELP;
		link.target = "_blank";
		link.rel = "noreferrer";
		link.textContent = "Create one";
		help.append(link, ` scoped to ${REPO} with read and write on Contents and Pull requests.`);
		body.appendChild(help);

		var save = document.createElement("button");
		save.type = "button";
		save.id = "edit-save-token";
		save.className = "edit-btn edit-primary";
		save.textContent = "Save token";
		save.addEventListener("click", () => {
			if (!input.value.trim()) return;
			writeToken(input.value.trim());
			refresh();
		});
		body.appendChild(footer(save));
	}

	function footer(...controls) {
		var row = document.createElement("div");
		row.className = "edit-footer";
		row.append(...controls);
		return row;
	}

	// A recipe is mostly unchanged, so the review shows the changed lines with a little
	// context and collapses the rest rather than making the reader hunt through the file
	var DIFF_CONTEXT = 2;

	function keptLines(ops) {
		var kept = new Set();
		ops.forEach((op, i) => {
			if (op.type === "same") return;
			for (var j = i - DIFF_CONTEXT; j <= i + DIFF_CONTEXT; j++) kept.add(j);
		});
		return kept;
	}

	function renderDiff(ops) {
		var view = document.createElement("pre");
		view.id = "edit-diff";
		view.className = "edit-diff";
		var kept = keptLines(ops);
		var skipped = 0;

		function flush() {
			if (skipped === 0) return;
			var gap = document.createElement("span");
			gap.className = "diff-skip";
			gap.textContent = `⋯ ${skipped} unchanged line${skipped === 1 ? "" : "s"}\n`;
			view.appendChild(gap);
			skipped = 0;
		}

		ops.forEach((op, i) => {
			if (!kept.has(i)) {
				skipped++;
				return;
			}
			flush();
			var line = document.createElement("span");
			line.className = `diff-${op.type}`;
			line.textContent = `${op.text}\n`;
			view.appendChild(line);
		});
		flush();
		return view;
	}

	function renderReview(body, source, text, photo, refresh) {
		var ops = diffLines(splitLines(source.text), splitLines(text));
		var changes = changedOps(ops);

		var status = document.createElement("p");
		status.id = "edit-status";
		status.className = "edit-help";

		if (changes.length === 0 && !photo) {
			status.textContent = "Nothing changed yet.";
			body.append(status, footer(backButton(refresh, source, text)));
			return;
		}

		body.appendChild(renderDiff(ops));
		if (photo) {
			var note = document.createElement("p");
			note.className = "edit-help";
			note.textContent = `Plus a new photo, resized to ${PHOTO_MAX_HEIGHT}px and stripped of its metadata.`;
			body.appendChild(note);
		}
		body.appendChild(status);

		var save = document.createElement("button");
		save.type = "button";
		save.id = "edit-submit";
		save.className = "edit-btn edit-primary";
		save.textContent = "Save to a pull request";
		save.addEventListener("click", async () => {
			save.disabled = true;
			try {
				var pr = await saveEdits(text, source.sha, photo, (message) => {
					status.textContent = message;
				});
				status.textContent = "";
				var done = document.createElement("a");
				done.href = pr.html_url;
				done.textContent = `Saved to pull request #${pr.number}`;
				status.appendChild(done);
				showPrBanner(await showPending());
			} catch (error) {
				status.textContent = error.message;
			} finally {
				save.disabled = false;
			}
		});

		body.appendChild(footer(backButton(refresh, source, text), save));
	}

	function backButton(refresh, source, text) {
		var back = document.createElement("button");
		back.type = "button";
		back.id = "edit-back";
		back.className = "edit-btn";
		back.textContent = "Back to editing";
		back.addEventListener("click", () => {
			refresh(source, text);
		});
		return back;
	}

	function renderEditor(body, source, draft, review) {
		var editor = document.createElement("textarea");
		editor.id = "edit-source";
		editor.className = "edit-source";
		editor.spellcheck = false;
		editor.value = draft ?? source.text;
		body.appendChild(editor);

		var photo = document.createElement("input");
		photo.type = "file";
		photo.id = "edit-photo";
		photo.className = "edit-input";
		photo.accept = "image/*";
		var photoField = document.createElement("label");
		photoField.className = "edit-field";
		photoField.append("Photo", photo);
		body.appendChild(photoField);

		var next = document.createElement("button");
		next.type = "button";
		next.id = "edit-review";
		next.className = "edit-btn edit-primary";
		next.textContent = "Review changes";
		next.addEventListener("click", () => {
			review(editor.value, photo.files[0] || null);
		});

		var revoke = document.createElement("button");
		revoke.type = "button";
		revoke.id = "edit-forget-token";
		revoke.className = "edit-quiet";
		revoke.textContent = "Forget token";
		revoke.addEventListener("click", () => {
			writeToken("");
			openDialog();
		});

		body.appendChild(footer(revoke, next));
	}

	function dialogElement() {
		var dialog = document.getElementById("edit-dialog");
		if (dialog) return dialog;
		dialog = document.createElement("dialog");
		dialog.id = "edit-dialog";
		dialog.className = "edit-dialog";
		var close = document.createElement("button");
		close.type = "button";
		close.className = "edit-close";
		close.setAttribute("aria-label", "Close");
		close.textContent = "×";
		close.addEventListener("click", () => {
			dialog.close();
		});
		var body = document.createElement("div");
		body.className = "edit-body";
		dialog.append(close, body);
		document.body.appendChild(dialog);
		return dialog;
	}

	function dialogBody() {
		var dialog = dialogElement();
		var body = dialog.querySelector(".edit-body");
		body.textContent = "";
		var heading = document.createElement("h2");
		heading.textContent = recipeTitle();
		body.appendChild(heading);
		return body;
	}

	function message(body, id, text) {
		var note = document.createElement("p");
		note.id = id;
		note.className = "edit-help";
		note.textContent = text;
		body.appendChild(note);
	}

	async function openDialog() {
		var body = dialogBody();
		var dialog = dialogElement();
		if (!dialog.open) dialog.showModal();

		if (!navigator.onLine) {
			message(body, "edit-offline", "Editing needs a connection. Nothing is saved on this device.");
			return;
		}
		if (!readToken()) {
			renderTokenForm(body, openDialog);
			return;
		}

		message(body, "edit-status", "Loading the source…");
		var branch = (await branchExists(branchName())) ? branchName() : BASE_BRANCH;
		var source = await readSource(branch);
		if (!source) {
			message(dialogBody(), "edit-status", `${sourcePath()} not found`);
			return;
		}
		showEditor(source);
	}

	function showEditor(source, draft) {
		renderEditor(dialogBody(), source, draft, (text, photo) => {
			renderReview(dialogBody(), source, text, photo, showEditor);
		});
	}

	async function loadOpenPr() {
		if (!readToken() || !navigator.onLine) return;
		try {
			openPr = await findOpenPr();
		} catch (_e) {
			openPr = null;
			return;
		}
		var unplaced = 0;
		try {
			unplaced = await showPending();
		} catch (_e) {
			unplaced = 0;
		}
		showPrBanner(unplaced);
	}

	function init() {
		var button = document.getElementById("edit-btn");
		if (!button) return;
		button.style.display = "inline-block";
		button.addEventListener("click", openDialog);
		loadOpenPr();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
