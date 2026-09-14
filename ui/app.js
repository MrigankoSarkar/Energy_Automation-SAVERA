/* ============================================================
   EnergyAutomation - UI Controller
   Final UI version
   - Professional notifications
   - Larger responsive typography support
   - Single frontend implementation
   - Existing backend bridge preserved
   ============================================================ */

"use strict";


/* ============================================================
   APPLICATION STATE
   ============================================================ */

let state = {
    settings: null,
    report: null,
    activity: []
};

let bridge = null;

const AppState = {
    nextRunAt: null,
    schedulerRunning: false,
    lastRefreshAt: null,
    notifications: new Map()
};


/* ============================================================
   HELPERS
   ============================================================ */

function $(id) {
    return document.getElementById(id);
}


function text(value, fallback = "") {
    if (value === null || value === undefined) {
        return fallback;
    }

    return String(value);
}


function escapeHtml(value) {
    return text(value).replace(
        /[&<>"']/g,
        function (character) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[character];
        }
    );
}


/* ============================================================
   NOTIFICATION SYSTEM
   ============================================================ */

function normalizeNotificationType(type) {
    const value = text(type, "info").toLowerCase();

    if (
        value === "success" ||
        value === "error" ||
        value === "warning" ||
        value === "info"
    ) {
        return value;
    }

    return "info";
}


function getNotificationMeta(type) {

    const metadata = {

        success: {
            title: "Automation successful",
            icon: "✓"
        },

        error: {
            title: "Action failed",
            icon: "×"
        },

        warning: {
            title: "Attention required",
            icon: "!"
        },

        info: {
            title: "Information",
            icon: "i"
        }
    };

    return metadata[type] || metadata.info;
}


function showToast(
    message,
    type = "info",
    duration = null,
    title = null
) {

    const container = $("globalNotifications");

    if (!container) {
        return null;
    }


    type = normalizeNotificationType(type);


    const defaultDurations = {

        success: 5000,
        info: 5500,
        warning: 7500,

        /* Error remains visible until user dismisses it. */
        error: 0
    };


    const timeout =
        duration === null
            ? defaultDurations[type]
            : Math.max(0, Number(duration));


    const metadata =
        getNotificationMeta(type);


    const notification =
        document.createElement("article");


    const id =
        "notification-" +
        Date.now() +
        "-" +
        Math.random()
            .toString(36)
            .slice(2, 8);


    notification.className =
        "global-notification " + type;


    notification.dataset.id =
        id;


    notification.setAttribute(
        "role",
        type === "error"
            ? "alert"
            : "status"
    );


    const timestamp =
        new Date().toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }
        );


    notification.innerHTML = `

        <div class="notification-accent"></div>

        <div
            class="notification-icon"
            aria-hidden="true"
        >
            ${metadata.icon}
        </div>

        <div class="notification-body">

            <div class="notification-heading">

                <strong>
                    ${escapeHtml(
                        title ||
                        metadata.title
                    )}
                </strong>

                <span class="notification-time">
                    ${escapeHtml(timestamp)}
                </span>

            </div>


            <div class="notification-message">

                ${escapeHtml(message)}

            </div>


            ${
                timeout > 0

                    ? `
                        <div
                            class="notification-progress"
                            aria-hidden="true"
                        >
                            <span></span>
                        </div>
                    `

                    : ""
            }

        </div>


        <button
            type="button"
            class="notification-close"
            aria-label="Dismiss notification"
            title="Dismiss"
        >
            ×
        </button>

    `;


    container.appendChild(
        notification
    );


    AppState.notifications.set(
        id,
        notification
    );


    function closeNotification() {

        if (
            !notification.parentElement
        ) {
            return;
        }


        if (notification._timer) {

            clearTimeout(
                notification._timer
            );
        }


        notification.classList.remove(
            "show"
        );


        notification.classList.add(
            "closing"
        );


        window.setTimeout(
            function () {

                notification.remove();

                AppState.notifications.delete(
                    id
                );

            },
            220
        );
    }


    const closeButton =
        notification.querySelector(
            ".notification-close"
        );


    if (closeButton) {

        closeButton.addEventListener(
            "click",
            closeNotification
        );
    }


    requestAnimationFrame(
        function () {

            requestAnimationFrame(
                function () {

                    notification.classList.add(
                        "show"
                    );

                }
            );

        }
    );


    if (timeout > 0) {

        const progressBar =
            notification.querySelector(
                ".notification-progress span"
            );


        if (progressBar) {

            progressBar.style.animationDuration =
                timeout + "ms";
        }


        notification._timer =
            window.setTimeout(
                closeNotification,
                timeout
            );
    }


    /*
     * Keep the notification center readable.
     * Maximum five visible notifications.
     */

    while (
        container.children.length > 5
    ) {

        const oldest =
            container.firstElementChild;


        if (
            oldest &&
            oldest._timer
        ) {

            clearTimeout(
                oldest._timer
            );
        }


        if (oldest) {
            oldest.remove();
        }
    }


    return id;
}


/*
 * Compatibility aliases.
 */

window.showToast =
    showToast;


window.toast =
    showToast;


/* ============================================================
   PAGE NAVIGATION
   ============================================================ */

function setPage(page) {

    document
        .querySelectorAll(".page")
        .forEach(
            function (element) {

                element.classList.toggle(
                    "active",
                    element.id === page
                );

            }
        );


    document
        .querySelectorAll(".nav-item")
        .forEach(
            function (button) {

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
            "Persistent local execution log."
        ],

        settings: [
            "Settings",
            "Configure Gmail, Excel and automation behavior."
        ]
    };


    const selected =
        titles[page] ||
        titles.dashboard;


    if ($("page-title")) {

        $("page-title").textContent =
            selected[0];
    }


    if ($("page-description")) {

        $("page-description").textContent =
            selected[1];
    }
}


/* ============================================================
   COMPONENT STATUS
   ============================================================ */

function statusText(status) {

    return text(
        status,
        "READY"
    ).toUpperCase();
}


function setComponent(
    stage,
    status,
    message
) {

    const map = {

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


    if (!map[stage]) {
        return;
    }


    const ids =
        map[stage];


    const pill =
        $(ids[0]);


    const value =
        $(ids[1]);


    const health =
        $(ids[2]);


    if (pill) {

        pill.textContent =
            statusText(status);
    }


    if (health) {

        health.textContent =
            statusText(status);
    }


    if (
        value &&
        message
    ) {

        const messageText =
            text(message);


        value.textContent =
            messageText.length > 34

                ? messageText.slice(
                    0,
                    34
                ) + "…"

                : messageText;
    }


    const className =

        status === "success"
            ? "success"

            : status === "error"
                ? "error"

                : status === "running"
                    ? "running"

                    : "";


    const step =
        $("stage-" + stage);


    if (step) {

        step.className =
            "pipeline-step " +
            className;
    }
}


/* ============================================================
   PROGRESS
   ============================================================ */

function progress(
    payload = {}
) {

    const percent =
        Math.max(
            0,
            Math.min(
                100,
                Number(
                    payload.percent || 0
                )
            )
        );


    if ($("progress-number")) {

        $("progress-number")
            .textContent =
            percent + "%";
    }


    if ($("progress-bar")) {

        $("progress-bar")
            .style.width =
            percent + "%";
    }


    if ($("pipeline-message")) {

        $("pipeline-message")
            .textContent =
            payload.message ||
            "Processing automation...";
    }


    if (payload.stage) {

        setComponent(
            payload.stage,
            payload.status,
            payload.message
        );
    }


    if ($("last-check")) {

        $("last-check")
            .textContent =
            new Date()
                .toLocaleTimeString();
    }
}


/* ============================================================
   ACTIVITY / HISTORY
   ============================================================ */

function renderActivity() {

    const rows =
        Array.isArray(state.activity)

            ? state.activity.slice(
                0,
                30
            )

            : [];


    if ($("activity-list")) {

        if (rows.length) {

            $("activity-list")
                .innerHTML =
                rows.map(
                    function (activity) {

                        return `

                            <div class="activity-item">

                                <span
                                    class="activity-status-dot"
                                ></span>

                                <span
                                    class="activity-time"
                                >
                                    ${escapeHtml(
                                        text(
                                            activity.timestamp
                                        ).slice(
                                            11,
                                            19
                                        ) ||
                                        activity.timestamp
                                    )}
                                </span>

                                <span
                                    class="activity-stage"
                                >
                                    ${escapeHtml(
                                        activity.stage ||
                                        "System"
                                    )}
                                </span>

                                <span
                                    class="activity-message"
                                >
                                    ${escapeHtml(
                                        activity.message ||
                                        ""
                                    )}
                                </span>

                            </div>

                        `;
                    }
                ).join("");

        } else {

            $("activity-list")
                .innerHTML = `

                    <div class="empty-state compact">

                        <div class="empty-icon">
                            ◷
                        </div>

                        <h2>
                            No activity yet
                        </h2>

                        <p>
                            Automation events will appear here
                            after the first execution.
                        </p>

                    </div>

                `;
        }
    }


    const historyHtml =

        rows.length

            ? rows.map(
                function (activity) {

                    return `

                        <div class="log-row">

                            <div class="log-stage">
                                ${escapeHtml(
                                    activity.stage ||
                                    "System"
                                )}
                            </div>

                            <div class="log-time">
                                ${escapeHtml(
                                    activity.timestamp ||
                                    ""
                                )}
                            </div>

                            <div class="log-message">
                                ${escapeHtml(
                                    activity.message ||
                                    ""
                                )}
                            </div>

                        </div>

                    `;
                }
            ).join("")

            : `

                <div class="empty-state large">

                    <div class="empty-icon">
                        ✓
                    </div>

                    <h2>
                        Execution history is empty
                    </h2>

                    <p>
                        Run the automation to begin
                        building the local execution history.
                    </p>

                </div>

            `;


    if ($("history-list")) {

        $("history-list")
            .innerHTML =
            historyHtml;
    }


    if ($("automation-log")) {

        $("automation-log")
            .innerHTML =
            historyHtml;
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


    const values = {

        "set-sender":
            settings.gmail?.sender ||
            "",

        "set-subject":
            settings.gmail?.subject_contains ||
            "",

        "set-days":
            settings.gmail?.search_days ??
            2,

        "set-file":
            settings.excel?.file ||
            "",

        "set-sheet":
            settings.excel?.worksheet ||
            "",

        "set-header":
            settings.excel?.header_row ??
            3,

        "set-date-col":
            settings.excel?.date_column ??
            2,

        "set-first-row":
            settings.excel?.first_data_row ??
            5,

        "set-total-col":
            settings.excel?.total_column ??
            18,

        "set-interval":
            settings.automation?.check_interval_minutes ??
            5
    };


    Object.keys(values)
        .forEach(
            function (id) {

                if ($(id)) {

                    $(id).value =
                        values[id];
                }
            }
        );


    if ($("set-auto")) {

        $("set-auto")
            .checked =
            !!settings
                .automation
                ?.start_automatically;
    }


    if ($("set-minimized")) {

        $("set-minimized")
            .checked =
            !!settings
                .automation
                ?.start_minimized;
    }
}


function saveSettings() {

    const settings =
        JSON.parse(
            JSON.stringify(
                state.settings ||
                {}
            )
        );


    settings.gmail =
        settings.gmail ||
        {};


    settings.excel =
        settings.excel ||
        {};


    settings.automation =
        settings.automation ||
        {};


    settings.gmail.sender =
        $("set-sender")
            ?.value
            .trim() ||
        "";


    settings.gmail.subject_contains =
        $("set-subject")
            ?.value
            .trim() ||
        "";


    settings.gmail.search_days =
        Number(
            $("set-days")
                ?.value ||
            2
        );


    settings.excel.file =
        $("set-file")
            ?.value
            .trim() ||
        "";


    settings.excel.worksheet =
        $("set-sheet")
            ?.value
            .trim() ||
        "";


    settings.excel.header_row =
        Number(
            $("set-header")
                ?.value ||
            3
        );


    settings.excel.date_column =
        Number(
            $("set-date-col")
                ?.value ||
            2
        );


    settings.excel.first_data_row =
        Number(
            $("set-first-row")
                ?.value ||
            5
        );


    settings.excel.total_column =
        Number(
            $("set-total-col")
                ?.value ||
            18
        );


    settings.automation
        .check_interval_minutes =
        Number(
            $("set-interval")
                ?.value ||
            5
        );


    settings.automation
        .start_automatically =
        !!$("set-auto")
            ?.checked;


    settings.automation
        .start_minimized =
        !!$("set-minimized")
            ?.checked;


    state.settings =
        settings;


    if (
        bridge &&
        typeof bridge.saveSettings ===
        "function"
    ) {

        bridge.saveSettings(
            JSON.stringify(
                settings
            )
        );


        showToast(
            "Settings were sent to the application and are being saved.",
            "success",
            4500,
            "Settings saved"
        );

    } else {

        showToast(
            "The application bridge is not available. Settings were not saved.",
            "error",
            0,
            "Settings unavailable"
        );
    }
}


/* ============================================================
   SCHEDULER
   ============================================================ */

function renderScheduler(
    scheduler
) {

    const running =
        !!scheduler?.running;


    AppState.schedulerRunning =
        running;


    if ($("scheduler-status")) {

        $("scheduler-status")
            .textContent =
            running
                ? "RUNNING"
                : "STOPPED";
    }


    if ($("scheduler-value")) {

        $("scheduler-value")
            .textContent =
            running
                ? "Running"
                : "Stopped";
    }


    if ($("scheduler-note")) {

        $("scheduler-note")
            .textContent =
            (
                scheduler?.interval ||
                state.settings
                    ?.automation
                    ?.check_interval_minutes ||
                5
            ) +
            " minute interval";
    }


    if ($("health-scheduler")) {

        $("health-scheduler")
            .textContent =
            running
                ? "RUNNING"
                : "STOPPED";
    }


    if ($("automation-status")) {

        $("automation-status")
            .textContent =
            running
                ? "RUNNING"
                : "STOPPED";


        $("automation-status")
            .classList.toggle(
                "stopped",
                !running
            );
    }


    if ($("automation-description")) {

        $("automation-description")
            .textContent =
            running

                ? "The application checks Gmail in the background."

                : "The scheduler is stopped. Run Now is still available.";
    }
}


function setNextRunTime(
    value
) {

    if (!value) {

        AppState.nextRunAt =
            null;

        updateCountdown();

        return;
    }


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        console.warn(
            "Invalid scheduler timestamp:",
            value
        );

        return;
    }


    AppState.nextRunAt =
        date;


    updateCountdown();
}


function updateCountdown() {

    const timer =
        $("nextRunTimer");


    const status =
        $("schedulerTimerStatus");


    if (!timer) {
        return;
    }


    if (!AppState.nextRunAt) {

        timer.textContent =
            "--:--:--";


        if (status) {

            status.textContent =
                "Waiting for scheduler";
        }


        return;
    }


    let seconds =
        Math.max(
            0,
            Math.floor(
                (
                    AppState.nextRunAt
                        .getTime() -
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

        String(hours)
            .padStart(2, "0")

        + ":" +

        String(minutes)
            .padStart(2, "0")

        + ":" +

        String(seconds)
            .padStart(2, "0");


    if (status) {

        status.textContent =

            hours === 0 &&
            minutes < 1

                ? "Automation starting soon"

                : "Next automatic check";
    }
}


function updateClock() {

    if ($("liveClock")) {

        $("liveClock")
            .textContent =
            new Date()
                .toLocaleTimeString(
                    [],
                    {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit"
                    }
                );
    }
}


/* ============================================================
   REPORT
   ============================================================ */

function renderReport(
    report
) {

    state.report =
        report;


    if (!report) {

        if ($("report-summary")) {

            $("report-summary")
                .innerHTML = `

                    <div class="empty-state compact">

                        <div class="empty-icon">
                            ▤
                        </div>

                        <h2>
                            No report processed yet
                        </h2>

                        <p>
                            The latest verified NBSense
                            report will appear here.
                        </p>

                    </div>

                `;
        }


        if ($("report-table")) {

            $("report-table")
                .innerHTML = "";
        }


        if ($("report-meta")) {

            $("report-meta")
                .textContent =
                "No report available.";
        }


        return;
    }


    if ($("report-summary")) {

        $("report-summary")
            .innerHTML = `

                <strong>
                    ${escapeHtml(
                        report.date ||
                        "—"
                    )}
                </strong>

                <br>

                <span>
                    ${escapeHtml(
                        report.subject ||
                        ""
                    )}
                </span>

                <br>

                <span>
                    ${Number(
                        report.updated
                            ?.length ||
                        0
                    )}
                    Excel cells updated ·
                    Total
                    ${escapeHtml(
                        report.total ??
                        "—"
                    )}
                    kWh
                </span>

            `;
    }


    if ($("report-meta")) {

        $("report-meta")
            .textContent =

            "Report date: " +
            text(
                report.date,
                "—"
            ) +

            " · Worksheet: " +

            text(
                report.worksheet,
                "—"
            ) +

            " · Excel row: " +

            text(
                report.row,
                "—"
            ) +

            " · Total: " +

            text(
                report.total,
                "—"
            ) +

            " kWh";
    }


    if (!$("report-table")) {
        return;
    }


    $("report-table")
        .innerHTML =

        (report.meters || [])
            .map(
                function (meter) {

                    const updated =
                        (
                            report.updated ||
                            []
                        ).find(
                            function (item) {

                                return (
                                    item.meter_name ===
                                    meter.meter_name
                                );
                            }
                        );


                    const energy =

                        meter.state ===
                        "N/A"

                            ? "N/A"

                            : text(
                                meter.active_energy,
                                "—"
                            ) +
                            " kWh";


                    const cell =
                        updated?.cell ||

                        (
                            meter.state ===
                            "N/A"

                                ? "Skipped"

                                : "Unmapped"
                        );


                    return `

                        <tr>

                            <td>
                                ${escapeHtml(
                                    meter.page ??
                                    "—"
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    meter.meter_name ||
                                    "—"
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    energy
                                )}
                            </td>

                            <td>

                                <span
                                    class="table-state ${
                                        meter.state ===
                                        "N/A"
                                            ? "na"
                                            : "ok"
                                    }"
                                >
                                    ${escapeHtml(
                                        meter.state ||
                                        "—"
                                    )}
                                </span>

                            </td>

                            <td>
                                ${escapeHtml(
                                    cell
                                )}
                            </td>

                        </tr>

                    `;
                }
            )
            .join("");
}


/* ============================================================
   BACKEND EVENTS
   ============================================================ */

function backendEvent(
    eventName,
    raw
) {

    let payload = {};


    try {

        payload =
            typeof raw === "string"

                ? JSON.parse(raw)

                : (
                    raw ||
                    {}
                );

    } catch (error) {

        console.error(
            "Could not parse backend event:",
            error
        );


        showToast(
            "The application returned an invalid event payload.",
            "error",
            0,
            "Backend event error"
        );


        return;
    }


    switch (eventName) {

        case "initialState":

            state =
                payload ||
                state;


            renderSettings(
                state.settings
            );


            renderScheduler(
                state.scheduler
            );


            renderActivity();


            renderReport(
                state.report
            );


            if (
                state.scheduler
                    ?.next_run_at
            ) {

                setNextRunTime(
                    state.scheduler
                        .next_run_at
                );
            }


            break;


        case "scheduler_state":

            renderScheduler(
                payload
            );


            if (
                payload.next_run_at
            ) {

                setNextRunTime(
                    payload.next_run_at
                );
            }


            break;


        case "next_run":

            setNextRunTime(
                payload.next_run_at
            );


            break;


        case "notification":

            showToast(

                payload.message ||
                "Application notification",

                payload.type ||
                "info",

                payload.duration ===
                undefined

                    ? null

                    : payload.duration,

                payload.title ||
                null
            );


            break;


        case "progress":

            progress(
                payload
            );


            renderActivity();


            break;


        case "report":

            renderReport(
                payload
            );


            break;


        case "settings":

            state.settings =
                payload;


            renderSettings(
                payload
            );


            break;


        case "success": {

            const report =
                payload.report ||
                payload;


            if (
                report &&
                (
                    report.date ||
                    report.meters ||
                    report.updated
                )
            ) {

                renderReport({

                    date:
                        report.date,

                    subject:
                        report.subject,

                    total:
                        report.total,

                    updated:
                        report.updated ||
                        [],

                    meters:
                        report.meters ||
                        [],

                    worksheet:
                        report.worksheet,

                    row:
                        report.row
                });
            }


            progress({

                stage:
                    "Scheduler",

                status:
                    "success",

                message:
                    "Automation completed successfully.",

                percent:
                    100
            });


            renderActivity();


            showToast(

                payload.message ||

                "The NBSense report was processed and the existing Excel workbook was updated successfully.",

                "success",

                6000,

                "Automation completed"
            );


            break;
        }


        case "waiting":

            progress({

                stage:
                    "Gmail",

                status:
                    "waiting",

                message:
                    payload.message ||
                    "Waiting for a new NBSense report.",

                percent:
                    10
            });


            showToast(

                payload.message ||
                "No new report is available yet.",

                "info",

                5500,

                "Waiting for report"
            );


            break;


        case "failure":

        case "error":

            progress({

                stage:
                    "Scheduler",

                status:
                    "error",

                message:
                    payload.message ||
                    "Automation failed.",

                percent:
                    0
            });


            showToast(

                payload.message ||
                "Automation failed.",

                "error",

                0,

                "Automation error"
            );


            renderActivity();


            break;


        default:

            console.debug(
                "Unhandled backend event:",
                eventName,
                payload
            );
    }
}


window.backendEvent =
    backendEvent;


/* ============================================================
   BRIDGE ACTIONS
   ============================================================ */

function callBridge(
    method,
    ...args
) {

    if (
        !bridge ||
        typeof bridge[method] !==
        "function"
    ) {

        showToast(

            "The " +
            method +
            " action is currently unavailable.",

            "error",

            0,

            "Application bridge unavailable"
        );


        return false;
    }


    try {

        bridge[method](
            ...args
        );


        return true;

    } catch (error) {

        console.error(
            "Bridge action failed:",
            method,
            error
        );


        showToast(

            "Could not execute " +
            method +
            ": " +
            (
                error.message ||
                error
            ),

            "error",

            0,

            "Action failed"
        );


        return false;
    }
}


/* ============================================================
   RUN NOW
   ============================================================ */

function runNow() {

    if (
        callBridge(
            "runNow"
        )
    ) {

        progress({

            stage:
                "Scheduler",

            status:
                "running",

            message:
                "Manual automation run started.",

            percent:
                5
        });


        showToast(

            "The automation run has started. Processing is running in the background.",

            "info",

            4500,

            "Automation started"
        );
    }
}


/* ============================================================
   REFRESH
   ============================================================ */

function refreshDashboard() {

    AppState.lastRefreshAt =
        new Date();


    if (
        callBridge(
            "refresh"
        )
    ) {

        showToast(

            "Application data is being refreshed.",

            "info",

            3000,

            "Refreshing"
        );
    }
}


/* ============================================================
   STOP
   ============================================================ */

function stopAutomation() {

    if (
        callBridge(
            "stop"
        )
    ) {

        showToast(

            "The scheduler stop command was sent successfully.",

            "warning",

            4500,

            "Scheduler stopping"
        );
    }
}


/* ============================================================
   DOM EVENTS
   ============================================================ */

function bindEvents() {

    document
        .querySelectorAll(
            ".nav-item"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        setPage(
                            button.dataset.page
                        );

                    }
                );

            }
        );


    if ($("run-btn")) {

        $("run-btn")
            .addEventListener(
                "click",
                runNow
            );
    }


    if ($("automation-run")) {

        $("automation-run")
            .addEventListener(
                "click",
                runNow
            );
    }


    if ($("refresh-btn")) {

        $("refresh-btn")
            .addEventListener(
                "click",
                refreshDashboard
            );
    }


    if ($("automation-refresh")) {

        $("automation-refresh")
            .addEventListener(
                "click",
                refreshDashboard
            );
    }


    if ($("automation-stop")) {

        $("automation-stop")
            .addEventListener(
                "click",
                stopAutomation
            );
    }


    if ($("save-settings")) {

        $("save-settings")
            .addEventListener(
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
        typeof QWebChannel ===
        "undefined" ||

        typeof qt ===
        "undefined" ||

        !qt.webChannelTransport
    ) {

        console.warn(
            "QWebChannel is not available."
        );


        return;
    }


    new QWebChannel(

        qt.webChannelTransport,

        function (channel) {

            bridge =
                channel.objects.bridge ||
                null;


            if (!bridge) {

                showToast(

                    "The application backend bridge could not be found.",

                    "error",

                    0,

                    "Backend connection failed"
                );


                return;
            }


            /*
             * Generic backend event signal.
             */

            if (
                bridge.event &&
                typeof bridge.event.connect ===
                "function"
            ) {

                bridge.event.connect(

                    function (
                        eventName,
                        payload
                    ) {

                        backendEvent(
                            eventName,
                            payload
                        );
                    }
                );
            }


            /*
             * Existing toast signal.
             */

            if (
                bridge.toast &&
                typeof bridge.toast.connect ===
                "function"
            ) {

                bridge.toast.connect(

                    function (
                        message,
                        type
                    ) {

                        showToast(
                            message,
                            type ||
                            "info"
                        );
                    }
                );
            }


            /*
             * Load initial state.
             */

            if (
                typeof bridge.getInitialState ===
                "function"
            ) {

                bridge.getInitialState(

                    function (raw) {

                        backendEvent(
                            "initialState",
                            raw
                        );
                    }
                );
            }

        }
    );
}


/* ============================================================
   APPLICATION STARTUP
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        bindEvents();


        updateClock();


        updateCountdown();


        window.setInterval(
            function () {

                updateClock();

                updateCountdown();

            },
            1000
        );


        initializeBridge();

    }
);