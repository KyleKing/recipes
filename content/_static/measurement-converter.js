function _convertMeasurement() {
	const value = parseFloat(document.getElementById("inputValue").value);
	const fromUnit = document.getElementById("inputUnit").value;
	const toUnit = document.getElementById("outputUnit").value;

	if (Number.isNaN(value)) {
		document.getElementById("result").innerHTML = "Please enter a valid number";
		return;
	}

	// Convert to ml first (base unit)
	const toMl = {
		cup: 236.588,
		tbsp: 14.787,
		tsp: 4.929,
		ml: 1,
		oz: 29.574,
	};

	const mlValue = value * toMl[fromUnit];
	const result = mlValue / toMl[toUnit];

	document.getElementById("result").innerHTML =
		`${value} ${fromUnit} = ${result.toFixed(2)} ${toUnit}`;
}
