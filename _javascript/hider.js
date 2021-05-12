// Add HTML and CSS for the modal and login form
function conceal() {
    document.body.innerHTML += `
        <div id="concealer-bg"></div>
        <div id="concealer-modal" class="modal">
            <form id="concealer-form">
                <label for="concealer-password">Password:</label>
                <input type="password" id="concealer-password" minlength="10" required>
                <!-- <button id="concealer-submit">Submit</button> -->
                <input type="submit" value="Submit">
            </form>
        </div>
    `;

    var style = document.createElement('style');
    document.head.appendChild(style);
    style.sheet.insertRule(`
        #concealer-bg {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            top: 0;
            background-color: darkseagreen;
            z-index: 9998;
        }
    `);
    style.sheet.insertRule(`
        #concealer-modal {
            display: block;
            background-color: white;
            left: 35%;
            margin: 15% auto;
            width: 30%;
            padding: 20px;
            position: absolute;
            top: 0;
            z-index: 9999;
        }
    `);
    style.sheet.insertRule(`
        #concealer-password {
            min-width: 70%;
            border-bottom: 1px solid grey;
        }
    `);

    function logSubmit(event) {
        // event.preventDefault();
        const pass = document.getElementById("concealer-password").value;
        if (pass[0] == "i" && pass.length >= 12) {
            createCookie("concealer-cookie", "alohomora", 365 * 10); // Valid 10 years
        }
        console.log("Password inspired by: https://www.tor.com/2021/04/28/the-angel-of-khan-el-khalili-p-djeli-clark/");
        console.log("...or you can cheat: https://github.com/KyleKing/recipes/blob/main/docs/_javascript/hider.js")
    }
    var form = document.getElementById('concealer-form');
    form.addEventListener('submit', logSubmit);
};

// Manage creating and accessing cookies. Based on: https://www.guru99.com/cookies-in-javascript-ultimate-guide.html
function createCookie(cookieName, cookieValue, daysToExpire) {
    var date = new Date();
    date.setTime(date.getTime() + (daysToExpire * 24 * 60 * 60 * 1000));
    document.cookie = cookieName + "=" + cookieValue + "; expires=" + date.toGMTString();
}
function accessCookie(cookieName) {
    var name = cookieName + "=";
    var allCookieArray = document.cookie.split(';');
    for (var i = 0; i < allCookieArray.length; i++) {
        var temp = allCookieArray[i].trim();
        if (temp.indexOf(name) == 0) {
            return temp.substring(name.length, temp.length);
        }
    }
    return "";
}

// Trigger modal only if the local cookies says so
if (accessCookie("concealer-cookie") != "alohomora") {
    conceal();
}
