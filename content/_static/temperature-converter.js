function _convertTemp() {
	const value = parseFloat(document.getElementById("tempValue").value);
	const unit = document.getElementById("tempUnit").value;

	if (Number.isNaN(value)) {
		document.getElementById("tempResult").innerHTML = "Please enter a valid temperature";
		return;
	}

	let result, resultUnit;

	if (unit === "f") {
		result = ((value - 32) * 5) / 9;
		resultUnit = "°C";
		document.getElementById("tempResult").innerHTML =
			`${value}°F = ${result.toFixed(1)}${resultUnit}`;
	} else {
		result = (value * 9) / 5 + 32;
		resultUnit = "°F";
		document.getElementById("tempResult").innerHTML =
			`${value}°C = ${result.toFixed(1)}${resultUnit}`;
	}
}
