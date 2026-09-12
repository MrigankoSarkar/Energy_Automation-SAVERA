"use strict";

/* ============================================================
   ENERGY AUTOMATION — FRONTEND
   Single QWebChannel architecture
   ============================================================ */

let bridge = null;

const state = {
    settings: null,
    report: null,
    activity: [],
    scheduler: {
        running: false,
        interval: 5,
        next_run_at: null
    }
};

let nextRunAt = null;


/* ============================================================
   DOM HELPER
   ============================================================ */

function $(id) {
    return document.getElementById(id);
}


function escapeHtml(value) {

    return String(value ?? "")
        .replace(
            /[&<>"']/g,
            character => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            })[character]
        );
}


/* ============================================================
   NOTIFICATIONS
   ============================================================ */

function showNotification(
    message,
    type = "info",
    duration = 4500
) {

    const container =
        $("globalNotifications");

    if (!container) {
        return;
    }

    const notification =
        document.createElement("div");

    notification.className =
        `global-notification ${type}`;

    const icons = {
        success: "✓",
        error: "×",
        warning: "!",
        info: "i"
    };

    notification.innerHTML = `
        <div class="notification-icon">
            ${icons[type] || "i"}
        </div>

        <div class="notification-content">

            <div class="notification-title">
                ${notificationTitle(type)}
            </div>

            <div class="notification-message">
                ${escapeHtml(message)}
            </div>

        </div>

        <button
            class="notification-close"
            aria-label="Close notification">
            ×
        </button>
    `;

    const closeButton =
        notification.querySelector(
            ".notification-close"
        );

    closeButton.onclick = () => {

        notification.classList.remove(
            "show"
        );

        setTimeout(
            () => notification.remove(),
            250
        );
    };

    container.appendChild(
        notification
    );

    requestAnimationFrame(
        () => {
            notification.classList.add(
                "show"
            );
        }
    );

    if (duration > 0) {

        setTimeout(
            () => {

                if (
                    notification.parentElement
                ) {

                    notification.classList.remove(
                        "show"
                    );

                    setTimeout(
                        () => notification.remove(),
                        250
                    );
                }

            },
            duration
        );
    }
}


function notificationTitle(type) {

    switch (type) {

        case "success":
            return "Completed";

        case "error":
            return "Error";

        case "warning":
            return "Attention";

        default:
            return "EnergyAutomation";
    }
}


function working(
    message
) {

    showNotification(
        message,
        "info",
        3000
    );
}


/* ============================================================
   PAGE NAVIGATION
   ============================================================ */

function setPage(
    page
) {

    document
        .querySelectorAll(".page")
        .forEach(
            element => {

                element.classList.toggle(
                    "active",
                    element.id === page
                );

            }
        );

    document
        .querySelectorAll(".nav-item")
        .forEach(
            button => {

                button.classList.toggle(
                    "active",
                    button.dataset.page === page
                );

            }
        );

    const titles = {

        dashboard: [
            "Energy Operations Dashboard",
            "Monitor Gmail, NBSense PDF processing, Excel updates and scheduler activity."
        ],

        automation: [
            "Automation Control",
            "Start, stop and inspect the live automation process."
        ],

        reports: [
            "Report Inspector",
            "Review extracted NBSense readings and Excel mapping."
        ],

        history: [
            "Activity History",
            "Review completed and failed automation executions."
        ],

        settings: [
            "Settings",
            "Configure Gmail, Excel and automation behavior."
        ]
    };

    if (titles[page]) {

        $("page-title").textContent =
            titles[page][0];

        $("page-description").textContent =
            titles[page][1];
    }

    showNotification(
        `${titles[page]?.[0] || page} opened.`,
        "info",
        1800
    );
}


/* ============================================================
   SCHEDULER
   ============================================================ */

function updateScheduler(
    scheduler
) {

    const running =
        Boolean(
            scheduler?.running
        );

    state.scheduler =
        scheduler || state.scheduler;

    nextRunAt =
        scheduler?.next_run_at
            ? new Date(
                scheduler.next_run_at
            )
            : null;

    const status =
        $("scheduler-status");

    const value =
        $("scheduler-value");

    const note =
        $("scheduler-note");

    const health =
        $("health-scheduler");

    const automationStatus =
        $("automation-status");

    const description =
        $("automation-description");

    if (status) {

        status.textContent =
            running
                ? "RUNNING"
                : "STOPPED";
    }

    if (value) {

        value.textContent =
            running
                ? "Running"
                : "Stopped";
    }

    if (note) {

        note.textContent =
            `${scheduler?.interval || 5} minute interval`;
    }

    if (health) {

        health.textContent =
            running
                ? "RUNNING"
                : "STOPPED";
    }

    if (automationStatus) {

        automationStatus.textContent =
            running
                ? "RUNNING"
                : "STOPPED";

        automationStatus.classList.toggle(
            "stopped",
            !running
        );
    }

    if (description) {

        description.textContent =
            running
                ? "Automatic EMS monitoring is active in the background."
                : "Automatic monitoring is stopped. Manual Run Now remains available.";
    }

    updateCountdown();
}


/* ============================================================
   COUNTDOWN
   ============================================================ */

function startTimer() {

    setInterval(
        () => {

            updateClock();
            updateCountdown();

        },
        1000
    );

    updateClock();
    updateCountdown();
}


function updateClock() {

    const clock =
        $("liveClock");

    if (!clock) {
        return;
    }

    clock.textContent =
        new Date().toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }
        );
}


function updateCountdown() {

    const timer =
        $("nextRunTimer");

    const status =
        $("schedulerTimerStatus");

    if (!timer) {
        return;
    }

    if (
        !nextRunAt ||
        Number.isNaN(
            nextRunAt.getTime()
        )
    ) {

        timer.textContent =
            "--:--:--";

        if (status) {

            status.textContent =
                state.scheduler.running
                    ? "Waiting for next check"
                    : "Scheduler stopped";
        }

        return;
    }

    let seconds = Math.max(
        0,
        Math.floor(
            (
                nextRunAt.getTime()
                -
                Date.now()
            ) / 1000
        )
    );

    const hours =
        Math.floor(
            seconds / 3600
        );

    seconds %= 3600;

    const minutes =
        Math.floor(
            seconds / 60
        );

    seconds %= 60;

    timer.textContent =
        `${String(hours).padStart(2, "0")}:` +
        `${String(minutes).padStart(2, "0")}:` +
        `${String(seconds).padStart(2, "0")}`;

    if (status) {

        if (
            hours === 0 &&
            minutes < 1
        ) {

            status.textContent =
                "Automation starting soon";

        } else {

            status.textContent =
                "Next automatic check";
        }
    }
}


/* ============================================================
   PROGRESS
   ============================================================ */

function updateProgress(
    payload
) {

    const percent =
        Number(
            payload.percent ?? 0
        );

    const progressNumber =
        $("progress-number");

    const progressBar =
        $("progress-bar");

    const message =
        $("pipeline-message");

    if (progressNumber) {

        progressNumber.textContent =
            `${percent}%`;
    }

    if (progressBar) {

        progressBar.style.width =
            `${Math.max(
                0,
                Math.min(
                    100,
                    percent
                )
            )}%`;
    }

    if (message) {

        message.textContent =
            payload.message ||
            "Processing...";
    }

    if (payload.stage) {

        updateComponent(
            payload.stage,
            payload.status ||
                "running",
            payload.message
        );
    }

    if (
        payload.message
    ) {

        addActivity(
            payload.stage ||
                "System",
            payload.message
        );
    }
}


/* ============================================================
   COMPONENT STATUS
   ============================================================ */

function updateComponent(
    stage,
    status,
    message
) {

    const mapping = {

        Gmail: [
            "gmail-status",
            "gmail-value",
            "health-gmail"
        ],

        PDF: [
            "pdf-status",
            "pdf-value",
            "health-pdf"
        ],

        Excel: [
            "excel-status",
            "excel-value",
            "health-excel"
        ],

        Scheduler: [
            "scheduler-status",
            "scheduler-value",
            "health-scheduler"
        ]
    };

    const ids =
        mapping[stage];

    if (!ids) {
        return;
    }

    const pill =
        $(ids[0]);

    const value =
        $(ids[1]);

    const health =
        $(ids[2]);

    const text =
        String(
            status ||
            "READY"
        ).toUpperCase();

    if (pill) {
        pill.textContent =
            text;
    }

    if (health) {
        health.textContent =
            text;
    }

    if (
        value &&
        message
    ) {

        value.textContent =
            message.length > 25
                ? `${message.slice(0, 25)}…`
                : message;
    }

    const step =
        $(`stage-${stage}`);

    if (step) {

        step.classList.remove(
            "success",
            "error",
            "running",
            "waiting"
        );

        step.classList.add(
            status || "running"
        );
    }
}


/* ============================================================
   ACTIVITY
   ============================================================ */

function addActivity(
    stage,
    message
) {

    state.activity.unshift({

        timestamp:
            new Date().toISOString(),

        stage:
            stage,

        message:
            message
    });

    state.activity =
        state.activity.slice(
            0,
            50
        );

    renderActivity();
}


function renderActivity() {

    const rows =
        state.activity || [];

    const activity =
        $("activity-list");

    const history =
        $("history-list");

    const automation =
        $("automation-log");


    if (activity) {

        activity.innerHTML =
            rows.length
                ? rows.slice(0, 30)
                    .map(
                        item => `
                            <div class="activity-item">

                                <span class="time">
                                    ${escapeHtml(
                                        item.timestamp
                                            ?.slice(11, 19)
                                            || ""
                                    )}
                                </span>

                                <span class="stage">
                                    ${escapeHtml(
                                        item.stage || "System"
                                    )}
                                </span>

                                <span class="message">
                                    ${escapeHtml(
                                        item.message || ""
                                    )}
                                </span>

                            </div>
                        `
                    )
                    .join("")
                : emptyMessage(
                    "No activity yet",
                    "Automation activity will appear here after the first execution."
                );
    }


    if (history) {

        history.innerHTML =
            rows.length
                ? rows.map(
                    item => `
                        <div class="log-row">

                            <strong>
                                ${escapeHtml(
                                    item.stage || "System"
                                )}
                            </strong>

                            <span>
                                ${escapeHtml(
                                    item.timestamp || ""
                                )}
                            </span>

                            <span>
                                ${escapeHtml(
                                    item.message || ""
                                )}
                            </span>

                        </div>
                    `
                ).join("")
                : emptyMessage(
                    "History is empty",
                    "Completed and failed executions will appear here."
                );
    }


    if (automation) {

        automation.innerHTML =
            rows.length
                ? rows.map(
                    item => `
                        <div class="log-row">

                            <strong>
                                ${escapeHtml(
                                    item.stage || "System"
                                )}
                            </strong>

                            <span>
                                ${escapeHtml(
                                    item.timestamp || ""
                                )}
                            </span>

                            <span>
                                ${escapeHtml(
                                    item.message || ""
                                )}
                            </span>

                        </div>
                    `
                ).join("")
                : emptyMessage(
                    "Waiting for automation",
                    "Execution stages will appear here when the automation starts."
                );
    }
}


function emptyMessage(
    title,
    description
) {

    return `
        <div class="empty-state enhanced-empty">

            <div class="empty-icon">
                ◌
            </div>

            <strong>
                ${escapeHtml(title)}
            </strong>

            <span>
                ${escapeHtml(description)}
            </span>

        </div>
    `;
}


/* ============================================================
   REPORT
   ============================================================ */

function renderReport(
    report
) {

    state.report =
        report;

    const summary =
        $("report-summary");

    const meta =
        $("report-meta");

    const table =
        $("report-table");

    if (!report) {

        if (summary) {

            summary.innerHTML =
                emptyMessage(
                    "No report processed yet",
                    "The latest NBSense report will appear here after automation runs."
                );
        }

        if (meta) {
            meta.textContent =
                "No report available.";
        }

        if (table) {
            table.innerHTML = "";
        }

        return;
    }


    if (summary) {

        summary.innerHTML = `
            <strong>
                ${escapeHtml(
                    report.date || "Unknown date"
                )}
            </strong>

            <br>

            <span>
                ${escapeHtml(
                    report.subject || "NBSense EMS Report"
                )}
            </span>

            <br><br>

            <span>
                ${report.updated?.length || 0}
                Excel cells updated
            </span>

            <br>

            <span>
                Total:
                ${report.total ?? "—"}
                kWh
            </span>
        `;
    }


    if (meta) {

        meta.textContent =
            `Report date: ${report.date || "—"} · ` +
            `Worksheet: ${report.worksheet || "—"} · ` +
            `Excel row: ${report.row || "—"} · ` +
            `Total: ${report.total ?? "—"} kWh`;
    }


    if (table) {

        table.innerHTML =
            (report.meters || [])
                .map(
                    meter => {

                        const updated =
                            (
                                report.updated ||
                                []
                            ).find(
                                item =>
                                    item.meter_name ===
                                    meter.meter_name
                            );

                        return `
                            <tr>

                                <td>
                                    ${escapeHtml(
                                        meter.page ?? ""
                                    )}
                                </td>

                                <td>
                                    ${escapeHtml(
                                        meter.meter_name ?? ""
                                    )}
                                </td>

                                <td>
                                    ${
                                        meter.state === "N/A"
                                            ? "N/A"
                                            : `${meter.active_energy ?? "—"} kWh`
                                    }
                                </td>

                                <td>
                                    ${escapeHtml(
                                        meter.state || "Processed"
                                    )}
                                </td>

                                <td>
                                    ${escapeHtml(
                                        updated?.cell ||
                                        (
                                            meter.state === "N/A"
                                                ? "Skipped"
                                                : "Unmapped"
                                        )
                                    )}
                                </td>

                            </tr>
                        `;
                    }
                )
                .join("");
    }
}


/* ============================================================
   SETTINGS
   ============================================================ */

function renderSettings(
    settings
) {

    if (!settings) {
        return;
    }

    state.settings =
        settings;

    const values = {

        "set-sender":
            settings.gmail?.sender || "",

        "set-subject":
            settings.gmail?.subject_contains || "",

        "set-days":
            settings.gmail?.search_days ?? 2,

        "set-file":
            settings.excel?.file || "",

        "set-sheet":
            settings.excel?.worksheet || "",

        "set-header":
            settings.excel?.header_row ?? 3,

        "set-date-col":
            settings.excel?.date_column ?? 2,

        "set-first-row":
            settings.excel?.first_data_row ?? 5,

        "set-total-col":
            settings.excel?.total_column ?? 18,

        "set-interval":
            settings.automation?.check_interval_minutes ?? 5
    };

    Object.entries(
        values
    ).forEach(
        ([id, value]) => {

            if ($(id)) {
                $(id).value =
                    value;
            }
        }
    );

    if ($("set-auto")) {

        $("set-auto").checked =
            Boolean(
                settings.automation
                    ?.start_automatically
            );
    }

    if ($("set-minimized")) {

        $("set-minimized").checked =
            Boolean(
                settings.automation
                    ?.start_minimized
            );
    }
}


/* ============================================================
   SAVE SETTINGS
   ============================================================ */

function saveSettings() {

    if (!bridge) {

        showNotification(
            "Backend connection is not ready.",
            "error"
        );

        return;
    }

    working(
        "Saving application settings..."
    );

    const settings =
        JSON.parse(
            JSON.stringify(
                state.settings || {}
            )
        );

    settings.gmail =
        settings.gmail || {};

    settings.excel =
        settings.excel || {};

    settings.automation =
        settings.automation || {};


    settings.gmail.sender =
        $("set-sender")?.value.trim() || "";

    settings.gmail.subject_contains =
        $("set-subject")?.value.trim() || "";

    settings.gmail.search_days =
        Number(
            $("set-days")?.value || 2
        );


    settings.excel.file =
        $("set-file")?.value.trim() || "";

    settings.excel.worksheet =
        $("set-sheet")?.value.trim() || "";

    settings.excel.header_row =
        Number(
            $("set-header")?.value || 3
        );

    settings.excel.date_column =
        Number(
            $("set-date-col")?.value || 2
        );

    settings.excel.first_data_row =
        Number(
            $("set-first-row")?.value || 5
        );

    settings.excel.total_column =
        Number(
            $("set-total-col")?.value || 18
        );


    settings.automation.check_interval_minutes =
        Number(
            $("set-interval")?.value || 5
        );

    settings.automation.start_automatically =
        Boolean(
            $("set-auto")?.checked
        );

    settings.automation.start_minimized =
        Boolean(
            $("set-minimized")?.checked
        );


    bridge.saveSettings(
        JSON.stringify(
            settings
        )
    );
}


/* ============================================================
   BUTTONS
   ============================================================ */

function runNow() {

    working(
        "Run Now selected — starting automation..."
    );

    if (!bridge) {

        showNotification(
            "Backend is not connected.",
            "error"
        );

        return;
    }

    bridge.runNow();
}


function stopAutomation() {

    working(
        "Stop selected — stopping automatic monitoring..."
    );

    if (!bridge) {

        showNotification(
            "Backend is not connected.",
            "error"
        );

        return;
    }

    bridge.stop();
}


function refreshApplication() {

    /*
     * IMPORTANT:
     *
     * This does not restart the timer.
     */

    working(
        "Refresh selected — updating application data..."
    );

    if (!bridge) {

        showNotification(
            "Backend is not connected.",
            "error"
        );

        return;
    }

    bridge.refresh();
}


/* ============================================================
   BACKEND EVENTS
   ============================================================ */

window.backendEvent =
function (
    eventName,
    raw
) {

    let payload = {};

    try {

        payload =
            typeof raw === "string"
                ? JSON.parse(raw)
                : raw || {};

    } catch (error) {

        showNotification(
            "Invalid backend response received.",
            "error"
        );

        console.error(
            error
        );

        return;
    }


    switch (eventName) {

        case "initialState":

            state.settings =
                payload.settings;

            state.report =
                payload.report;

            state.activity =
                payload.activity || [];

            renderSettings(
                state.settings
            );

            renderScheduler(
                payload.scheduler
            );

            renderActivity();

            renderReport(
                state.report
            );

            break;


        case "settings":

            renderSettings(
                payload
            );

            break;


        case "scheduler_state":

            renderScheduler(
                payload
            );

            break;


        case "next_run":

            nextRunAt =
                payload.next_run_at
                    ? new Date(
                        payload.next_run_at
                    )
                    : null;

            updateCountdown();

            break;


        case "progress":

            updateProgress(
                payload
            );

            break;


        case "notification":

            showNotification(
                payload.message ||
                    "Application event.",
                payload.type ||
                    "info",
                payload.duration ||
                    4500
            );

            addActivity(
                "System",
                payload.message ||
                    "Application event."
            );

            break;


        case "report":

            renderReport(
                payload
            );

            break;


        case "automation_result":

            handleAutomationResult(
                payload
            );

            break;


        case "success":

            handleSuccess(
                payload
            );

            break;


        case "error":

            handleError(
                payload
            );

            break;


        case "waiting":

            updateProgress({
                stage: "Gmail",
                status: "waiting",
                message:
                    payload.message ||
                    "Waiting for a new NBSense report.",
                percent: 10
            });

            showNotification(
                payload.message ||
                    "No new report found.",
                "info"
            );

            break;
    }
};


/* ============================================================
   SCHEDULER RENDER
   ============================================================ */

function renderScheduler(
    scheduler
) {

    state.scheduler =
        scheduler || state.scheduler;

    nextRunAt =
        scheduler?.next_run_at
            ? new Date(
                scheduler.next_run_at
            )
            : null;

    updateScheduler(
        scheduler
    );
}


/* ============================================================
   AUTOMATION RESULT
   ============================================================ */

function handleAutomationResult(
    result
) {

    if (!result) {
        return;
    }

    if (result.success === false) {

        handleError(
            {
                message:
                    result.error ||
                    "Automation failed."
            }
        );

        return;
    }

    if (result.report) {

        renderReport(
            result.report
        );
    }

    if (result.excel) {

        const count =
            result.excel.updated?.length ||
            0;

        showNotification(
            `Automation completed. ${count} Excel cell(s) updated.`,
            "success",
            6000
        );
    }
}


/* ============================================================
   SUCCESS
   ============================================================ */

function handleSuccess(
    payload
) {

    const report =
        payload.report;

    if (report) {

        renderReport(
            report
        );
    }

    updateProgress({
        stage: "Scheduler",
        status: "success",
        message:
            "Automation completed successfully.",
        percent: 100
    });

    showNotification(
        payload.message ||
            "Automation completed successfully.",
        "success",
        5500
    );
}


/* ============================================================
   ERROR
   ============================================================ */

function handleError(
    payload
) {

    const message =
        payload.message ||
        "Automation failed.";

    updateProgress({
        stage: "Scheduler",
        status: "error",
        message: message,
        percent: 0
    });

    addActivity(
        "ERROR",
        message
    );

    showNotification(
        message,
        "error",
        9000
    );
}


/* ============================================================
   COACH MARKS
   ============================================================ */

const coachSteps = [

    {
        selector:
            ".brand",

        title:
            "Welcome to EnergyAutomation",

        text:
            "This application automatically finds NBSense EMS reports, extracts energy readings and updates the existing Excel workbook."
    },

    {
        selector:
            "#nextRunTimer",

        title:
            "Automatic scheduler",

        text:
            "This countdown shows when the next automatic EMS check will run. Refreshing the application does not reset this timer."
    },

    {
        selector:
            "#run-btn",

        title:
            "Run Now",

        text:
            "Use Run Now when you want to execute the complete Gmail → PDF → Excel workflow immediately."
    },

    {
        selector:
            "#refresh-btn",

        title:
            "Refresh",

        text:
            "Refresh updates application information without restarting the scheduler."
    },

    {
        selector:
            '[data-page="reports"]',

        title:
            "Reports",

        text:
            "Open Reports to inspect extracted meter readings and their Excel cell mappings."
    },

    {
        selector:
            '[data-page="history"]',

        title:
            "History",

        text:
            "Execution history records what the automation has done, including successful and failed operations."
    },

    {
        selector:
            '[data-page="settings"]',

        title:
            "Settings",

        text:
            "Configure Gmail search, Excel workbook, worksheet and scheduler behavior here."
    }
];


let coachIndex = 0;


function createCoachMarks() {

    if (
        document.getElementById(
            "coach-overlay"
        )
    ) {
        return;
    }

    const overlay =
        document.createElement("div");

    overlay.id =
        "coach-overlay";

    overlay.innerHTML = `
        <div id="coach-backdrop"></div>

        <div id="coach-card">

            <div class="coach-progress">
                <span id="coach-step">
                    1 / ${coachSteps.length}
                </span>
            </div>

            <h3 id="coach-title">
                Welcome
            </h3>

            <p id="coach-text">
                Learn how to use EnergyAutomation.
            </p>

            <div class="coach-actions">

                <button
                    id="coach-skip"
                    class="coach-link">
                    Skip tour
                </button>

                <div>

                    <button
                        id="coach-prev"
                        class="btn btn-secondary">
                        Previous
                    </button>

                    <button
                        id="coach-next"
                        class="btn btn-primary">
                        Next
                    </button>

                </div>

            </div>

        </div>
    `;

    document.body.appendChild(
        overlay
    );

    $("coach-next").onclick =
        nextCoachStep;

    $("coach-prev").onclick =
        previousCoachStep;

    $("coach-skip").onclick =
        closeCoachMarks;

    showCoachStep();
}


function showCoachStep() {

    const step =
        coachSteps[coachIndex];

    if (!step) {
        return;
    }

    document
        .querySelectorAll(
            ".coach-highlight"
        )
        .forEach(
            element =>
                element.classList.remove(
                    "coach-highlight"
                )
        );

    const target =
        document.querySelector(
            step.selector
        );

    if (target) {

        target.classList.add(
            "coach-highlight"
        );

        target.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });
    }

    $("coach-step").textContent =
        `${coachIndex + 1} / ${coachSteps.length}`;

    $("coach-title").textContent =
        step.title;

    $("coach-text").textContent =
        step.text;

    $("coach-prev").disabled =
        coachIndex === 0;

    $("coach-next").textContent =
        coachIndex ===
        coachSteps.length - 1
            ? "Finish"
            : "Next";
}


function nextCoachStep() {

    if (
        coachIndex <
        coachSteps.length - 1
    ) {

        coachIndex++;

        showCoachStep();

    } else {

        closeCoachMarks();
    }
}


function previousCoachStep() {

    if (
        coachIndex > 0
    ) {

        coachIndex--;

        showCoachStep();
    }
}


function closeCoachMarks() {

    const overlay =
        $("coach-overlay");

    if (overlay) {

        overlay.remove();
    }

    document
        .querySelectorAll(
            ".coach-highlight"
        )
        .forEach(
            element =>
                element.classList.remove(
                    "coach-highlight"
                )
        );

    localStorage.setItem(
        "energyautomation-coach-completed",
        "1"
    );
}


/* ============================================================
   TOOLTIPS
   ============================================================ */

function installTooltips() {

    document
        .querySelectorAll(
            "button"
        )
        .forEach(
            button => {

                if (
                    !button.title
                ) {

                    const text =
                        button.textContent
                            .trim();

                    if (text) {

                        button.title =
                            text;
                    }
                }
            }
        );

    const tooltipTargets = {

        "#run-btn":
            "Run the complete EMS automation immediately.",

        "#refresh-btn":
            "Refresh application information without resetting the scheduler.",

        "#automation-run":
            "Run the EMS workflow immediately.",

        "#automation-stop":
            "Stop future automatic scheduler executions.",

        "#automation-refresh":
            "Refresh application information without resetting the timer.",

        "#nextRunTimer":
            "Time remaining until the next automatic EMS check.",

        "#save-settings":
            "Save configuration changes to settings.json."
    };

    Object.entries(
        tooltipTargets
    ).forEach(
        ([selector, text]) => {

            const element =
                document.querySelector(
                    selector
                );

            if (element) {

                element.setAttribute(
                    "data-tooltip",
                    text
                );
            }
        }
    );
}


/* ============================================================
   NAVIGATION BUTTONS
   ============================================================ */

function installNavigation() {

    document
        .querySelectorAll(
            ".nav-item"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        const page =
                            button.dataset.page;

                        setPage(
                            page
                        );
                    }
                );
            }
        );
}


/* ============================================================
   BUTTON INSTALLATION
   ============================================================ */

function installButtons() {

    const run =
        $("run-btn");

    if (run) {

        run.addEventListener(
            "click",
            runNow
        );
    }


    const refresh =
        $("refresh-btn");

    if (refresh) {

        refresh.addEventListener(
            "click",
            refreshApplication
        );
    }


    const automationRun =
        $("automation-run");

    if (automationRun) {

        automationRun.addEventListener(
            "click",
            runNow
        );
    }


    const automationStop =
        $("automation-stop");

    if (automationStop) {

        automationStop.addEventListener(
            "click",
            stopAutomation
        );
    }


    const automationRefresh =
        $("automation-refresh");

    if (automationRefresh) {

        automationRefresh.addEventListener(
            "click",
            refreshApplication
        );
    }


    const save =
        $("save-settings");

    if (save) {

        save.addEventListener(
            "click",
            saveSettings
        );
    }
}


/* ============================================================
   QWEBCHANNEL
   ============================================================ */

function initializeBridge() {

    if (
        typeof qt === "undefined" ||
        !qt.webChannelTransport
    ) {

        showNotification(
            "Qt WebChannel is unavailable.",
            "error",
            10000
        );

        return;
    }


    new QWebChannel(
        qt.webChannelTransport,
        channel => {

            bridge =
                channel.objects.bridge;

            if (!bridge) {

                showNotification(
                    "Python backend bridge was not found.",
                    "error",
                    10000
                );

                return;
            }

            showNotification(
                "Python automation backend connected.",
                "success",
                3000
            );


            if (
                typeof bridge.getInitialState ===
                "function"
            ) {

                bridge.getInitialState(
                    raw => {

                        try {

                            const initial =
                                JSON.parse(
                                    raw
                                );

                            backendEvent(
                                "initialState",
                                initial
                            );

                        } catch (error) {

                            showNotification(
                                "Could not load initial application state.",
                                "error"
                            );

                            console.error(
                                error
                            );
                        }
                    }
                );
            }
        }
    );
}


/* ============================================================
   APPLICATION START
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        installNavigation();

        installButtons();

        installTooltips();

        startTimer();

        initializeBridge();

        renderActivity();

        renderReport(
            null
        );

        if (
            !localStorage.getItem(
                "energyautomation-coach-completed"
            )
        ) {

            setTimeout(
                createCoachMarks,
                1200
            );
        }
    }
);