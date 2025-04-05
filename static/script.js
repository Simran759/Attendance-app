let isAdmin = false;
let deviceId = "";
const API_BASE_URL = "https://attendance-appli-1te1.vercel.app"; // Replace with your deployment URL when live
document.addEventListener("DOMContentLoaded", async () => {
    deviceId = await generateDeviceId();

    // // Check for developer tools
    detectDevTools();

    // Check for potential mock location
    checkLocationMock();

    document.getElementById("admin-login-btn").addEventListener("click", handleAdminLogin);
    document.getElementById("checkin-btn").addEventListener("click", handleCheckIn);
    document.getElementById("submit-location-btn").addEventListener("click", submitAdminLocation);
});

function detectDevTools() {
    const devtools = /./;
    devtools.toString = function () {
        this.opened = true;
    };

    setInterval(() => {
        console.log(devtools);
        if (devtools.opened) {
            alert("Developer tools detected. Please close it to continue.");
            window.location.reload();
        }
    }, 1000);
}

async function checkLocationMock() {
    if (!navigator.geolocation) {
        alert("Geolocation not supported!");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            accuracy = pos.coords.accuracy;
            if (accuracy > 200) {
                alert("Location accuracy too low. Spoofed location suspected.");
                // Optional: block further actions
            }
        },
        (err) => {
            alert("Error fetching location.");
        },
        { enableHighAccuracy: true }
    );
}
async function generateDeviceId() {
    try {
        const fpPromise = FingerprintJS.load();
        const fp = await fpPromise;
        const result = await fp.get();
        return result.visitorId; // Unique device fingerprint
    } catch (error) {
        console.error("Error generating device ID:", error);
        return "unknown-device";
    }
}

async function handleAdminLogin() {
    const adminId = document.getElementById("admin-id").value;
    const adminPassword = document.getElementById("admin-password").value;
    console.log("Logging in...");
    const response = await fetch(`${API_BASE_URL}/admin_login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_id: adminId, password: adminPassword })
    });

    const data = await response.json();
    alert(data.message);

    if (response.ok) {
        isAdmin = true;
        document.getElementById("login-section").style.display = "none";
        document.getElementById("admin-dashboard").style.display = "block";
        fetchAttendance();
    }
}

async function submitAdminLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            const { latitude, longitude } = position.coords;

            const response = await fetch(`${API_BASE_URL}/admin_location`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ latitude, longitude })
            });

            const data = await response.json();
            // alert(data);
            alert("Admin location updated!");
        }, () => {
            alert("Location access is required.");
        });
    }
}

async function handleCheckIn() {
    const studentId = document.getElementById("student-id").value;
    const name = document.getElementById("student-name").value;

    if (!studentId || !name) {
        alert("Please enter all fields.");
        return;
    }

    navigator.geolocation.getCurrentPosition(async (position) => {
        const { latitude, longitude,accuracy } = position.coords;

        const studentData = { student_id: studentId, name, latitude, longitude, device_id: deviceId ,accuracy:accuracy};
        console.log(studentData);
        const response = await fetch(`${API_BASE_URL}/student_checkin`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(studentData)
        });

        const data = await response.json();

        if (data.warning) {
            alert(data.warning);
        } else {
            alert("Check-in successful!");
            await markAttendance(studentData);
        }
    }, () => {
        alert("Location access is required for check-in.");
    });
}

async function markAttendance(studentData) {
    const response = await fetch(`${API_BASE_URL}/mark_attendance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(studentData)
    });

    const data = await response.json();

    if (data.warning) {
        alert(data.warning);
    } else {
        alert("Attendance marked successfully!");
        fetchAttendance();
    }
}

async function fetchAttendance() {
    try {
        const response = await fetch(`${API_BASE_URL}/attendance`);
        const data = await response.json();

        let presentCountElem = document.getElementById("present-count");
        let proxyCountElem = document.getElementById("proxy-count");
        let presentList = document.getElementById("present-students");
        let proxyList = document.getElementById("proxy-students");

        if (!presentCountElem || !proxyCountElem || !presentList || !proxyList) {
            console.error("Error: Missing attendance elements in the DOM.");
            return;
        }

        presentCountElem.textContent = `Total Present: ${data.total_present}`;
        proxyCountElem.textContent = `Total Proxies: ${data.total_proxy}`;

        presentList.innerHTML = "";
        proxyList.innerHTML = "";

        data.students.forEach(student => {
            const listItem = document.createElement("li");
            listItem.textContent = `${student.name} - ${student.student_id}`;
            
            if (student.status === "Present") {
                listItem.classList.add("green");
                presentList.appendChild(listItem);
            } else {
                listItem.classList.add("red");
                proxyList.appendChild(listItem);
            }
        });
    } catch (error) {
        console.error("Error fetching attendance:", error);
    }
}
