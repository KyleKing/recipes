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

	async function ensureBranch() {
		var branch = branchName();
		if (await api(`/repos/${REPO}/git/ref/heads/${branch}`)) return branch;

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

	function currentRating() {
		return document.querySelector(".recipe-rating")?.dataset.rating ?? "";
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

	async function saveEdits(rating, photo, report) {
		report("Preparing the branch…");
		var branch = await ensureBranch();

		var source = await readFile(sourcePath(), branch);
		if (!source) throw new Error(`${sourcePath()} not found on ${branch}`);
		var text = decodeBase64(source.content);

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

		if (rating !== currentRating()) {
			text = replaceMetadata(text, "rating", rating);
		}

		report("Committing…");
		await commitFile(
			sourcePath(),
			branch,
			encodeBase64(text),
			source.sha,
			`feat(recipe): update ${recipeTitle()}`,
		);

		report("Opening the pull request…");
		openPr = await ensurePr(branch, `Recipe edits: ${recipeTitle()}`);
		showPrBanner();
		return openPr;
	}

	function showPrBanner() {
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
	}

	function field(parent, labelText, control) {
		var label = document.createElement("label");
		label.className = "edit-field";
		label.append(labelText, control);
		parent.appendChild(label);
		return control;
	}

	function renderTokenForm(body, refresh) {
		var input = document.createElement("input");
		input.type = "password";
		input.id = "edit-token";
		input.autocomplete = "off";
		field(body, "Fine-grained token", input);

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
		save.className = "edit-btn";
		save.textContent = "Save token";
		save.addEventListener("click", () => {
			if (!input.value.trim()) return;
			writeToken(input.value.trim());
			refresh();
		});
		body.appendChild(save);
	}

	function renderEditForm(body, refresh) {
		var rating = document.createElement("select");
		rating.id = "edit-rating";
		["0", "1", "2", "3", "4", "5"].forEach((value) => {
			var option = document.createElement("option");
			option.value = value;
			option.textContent = value === "0" ? "Not yet rated" : `${value} / 5`;
			rating.appendChild(option);
		});
		rating.value = currentRating() || "0";
		field(body, "Rating", rating);

		var photo = document.createElement("input");
		photo.type = "file";
		photo.id = "edit-photo";
		photo.accept = "image/*";
		field(body, "Photo", photo);

		var status = document.createElement("p");
		status.id = "edit-status";
		status.className = "edit-help";
		body.appendChild(status);

		function report(message) {
			status.textContent = message;
		}

		var save = document.createElement("button");
		save.type = "button";
		save.id = "edit-submit";
		save.className = "edit-btn";
		save.textContent = "Save to a pull request";
		save.addEventListener("click", async () => {
			save.disabled = true;
			try {
				var pr = await saveEdits(rating.value, photo.files[0] || null, report);
				report("");
				var done = document.createElement("a");
				done.href = pr.html_url;
				done.textContent = `Saved to pull request #${pr.number}`;
				status.appendChild(done);
			} catch (error) {
				report(error.message);
			} finally {
				save.disabled = false;
			}
		});
		body.appendChild(save);

		var revoke = document.createElement("button");
		revoke.type = "button";
		revoke.id = "edit-forget-token";
		revoke.className = "edit-btn";
		revoke.textContent = "Forget token on this device";
		revoke.addEventListener("click", () => {
			writeToken("");
			refresh();
		});
		body.appendChild(revoke);
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

	function renderDialog() {
		var dialog = dialogElement();
		var body = dialog.querySelector(".edit-body");
		body.textContent = "";

		var heading = document.createElement("h2");
		heading.textContent = `Edit ${recipeTitle()}`;
		body.appendChild(heading);

		if (!navigator.onLine) {
			var offline = document.createElement("p");
			offline.id = "edit-offline";
			offline.className = "edit-help";
			offline.textContent = "Editing needs a connection. Nothing is saved on this device.";
			body.appendChild(offline);
			return dialog;
		}

		if (readToken()) renderEditForm(body, renderDialog);
		else renderTokenForm(body, renderDialog);
		return dialog;
	}

	async function loadOpenPr() {
		if (!readToken() || !navigator.onLine) return;
		try {
			openPr = await findOpenPr();
		} catch (_e) {
			openPr = null;
		}
		showPrBanner();
	}

	function init() {
		var button = document.getElementById("edit-btn");
		if (!button) return;
		button.style.display = "inline-block";
		button.addEventListener("click", () => {
			renderDialog().showModal();
		});
		loadOpenPr();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
