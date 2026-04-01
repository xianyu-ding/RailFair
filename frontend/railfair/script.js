// Configuration
// 直接硬编码后端 API 地址，确保不会使用错误的前端域名
// 后端 API 域名是 https://api.railfair.uk
// 强制设置为 api.railfair.uk，忽略任何其他配置
const API_BASE = 'https://api.railfair.uk';
const API_URL = 'https://api.railfair.uk';  // 直接硬编码，不使用任何变量
console.log('🔧 API Configuration:', { API_BASE, API_URL });
const CANVAS_ID = 'rain-canvas';

/** Only show trains whose departure is within this many minutes of the search (or “load more”) anchors. */
const NEARBY_WINDOW_MINUTES = 120;

// State
let stations = [];
let animationFrameId;
let currentTimetables = [];
let currentPagination = null;
let currentSearchParams = null;

let sessionAllTimetables = [];
let originalSearchAnchor = null;
let extraAnchorWindows = [];
let latestPredictionForCards = null;
let latestFaresForCards = null;
let latestPagination = null;
let showAllServicesToday = false;

// DOM Elements
const canvas = document.getElementById(CANVAS_ID);
const ctx = canvas.getContext('2d');
const searchForm = document.getElementById('search-form');
const mainContainer = document.getElementById('main-container');
const heroText = document.getElementById('hero-text');
const searchCard = document.getElementById('search-card');
const resultsContainer = document.getElementById('results-container');
const resultsList = document.getElementById('results-list');
const searchBtn = document.getElementById('search-btn');

// --- Animation System (Clean Data Rain) ---
const RAIN_DATA_SNIPPETS = [
    "ON_TIME", "LNER_800", "£67.50",
    "KGX→MAN", "DLY_03M", "PLAT_05",
    "98%", "SYNC_OK", "KGX",
    "GWR", "£122.30", "CANCEL",
    "AVANTI", "101101", "SPEED_OK"
];

class Particle {
    constructor(width, height) {
        this.reset(width, height);
        this.y = Math.random() * height;
    }

    reset(width, height) {
        this.x = Math.random() * width;
        this.y = -50;
        this.speed = 0.6 + Math.random() * 1.2;
        this.text = RAIN_DATA_SNIPPETS[Math.floor(Math.random() * RAIN_DATA_SNIPPETS.length)];
        this.opacity = 0.12 + Math.random() * 0.28;
        this.size = 13;

        if (this.text.includes("OK") || this.text.includes("%")) {
            this.color = "rgba(37, 99, 235,"; // Blue-600
        } else {
            this.color = "rgba(100, 116, 139,"; // Slate-500
        }
    }

    update(height) {
        this.y += this.speed;
        if (this.y > height + 50) {
            this.reset(canvas.width, canvas.height);
        }
    }

    draw(ctx) {
        ctx.font = `500 ${this.size}px 'Inter', sans-serif`;
        ctx.fillStyle = `${this.color} ${this.opacity})`;
        ctx.fillText(this.text, this.x, this.y);
    }
}

let particles = [];

function initAnimation() {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Create particles
    for (let i = 0; i < 40; i++) {
        particles.push(new Particle(canvas.width, canvas.height));
    }

    animate();
}

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight * 0.6; // Cover top 60%
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    particles.forEach(p => {
        p.update(canvas.height);
        p.draw(ctx);
    });

    animationFrameId = requestAnimationFrame(animate);
}

// --- Data Handling ---
async function loadStations() {
    try {
        const response = await fetch('stations.json');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        stations = data.StationList || data.stations || [];
        console.log('Loaded stations:', stations.length);
    } catch (error) {
        console.error('Failed to load stations:', error);
        // Fallback to a more comprehensive list
        stations = [
            { crs: 'EUS', Value: 'London Euston' },
            { crs: 'MAN', Value: 'Manchester Piccadilly' },
            { crs: 'KGX', Value: 'London Kings Cross' },
            { crs: 'PAD', Value: 'London Paddington' },
            { crs: 'BRI', Value: 'Bristol Temple Meads' },
            { crs: 'BHM', Value: 'Birmingham New Street' },
            { crs: 'LIV', Value: 'Liverpool Lime Street' },
            { crs: 'LDS', Value: 'Leeds' },
            { crs: 'NCL', Value: 'Newcastle' },
            { crs: 'EDB', Value: 'Edinburgh Waverley' },
            { crs: 'GLC', Value: 'Glasgow Central' }
        ];
        console.log('Using fallback stations:', stations.length);
    }
}

function setupAutocomplete(inputId, suggestionsId) {
    const input = document.getElementById(inputId);
    const suggestions = document.getElementById(suggestionsId);

    if (!input || !suggestions) {
        console.error(`Autocomplete setup failed: input=${inputId}, suggestions=${suggestionsId}`);
        return;
    }

    input.addEventListener('input', () => {
        const query = input.value.trim().toLowerCase();
        console.log('Autocomplete input:', query, 'stations count:', stations.length);

        if (query.length < 1) {
            suggestions.classList.add('hidden');
            return;
        }

        if (!stations || stations.length === 0) {
            console.warn('No stations loaded yet');
            suggestions.classList.add('hidden');
            return;
        }

        const matches = stations.filter(s => {
            const valueMatch = s.Value && s.Value.toLowerCase().includes(query);
            const crsMatch = s.crs && s.crs.toLowerCase().includes(query);
            return valueMatch || crsMatch;
        }).slice(0, 8);

        console.log('Autocomplete matches:', matches.length);

        suggestions.innerHTML = '';
        if (matches.length > 0) {
            matches.forEach(s => {
                const div = document.createElement('div');
                div.className = 'px-4 py-3 hover:bg-slate-50 cursor-pointer text-sm text-slate-700 border-b border-slate-50 last:border-0';
                div.textContent = `${s.Value || s.name || ''} (${s.crs || ''})`;
                div.onclick = () => {
                    input.value = (s.crs || '').toUpperCase();
                    suggestions.classList.add('hidden');
                };
                suggestions.appendChild(div);
            });
            suggestions.classList.remove('hidden');
        } else {
            suggestions.classList.add('hidden');
        }
    });

    document.addEventListener('click', (e) => {
        if (e.target !== input && !suggestions.contains(e.target)) {
            suggestions.classList.add('hidden');
        }
    });
}

function normalizeApiPayload(response) {
    if (response && response.data && response.data.prediction) {
        return response.data;
    }
    return response;
}

/** Cloudflare Workers build returns a lone `timetable` without `service_id`; FastAPI+NRDP returns `timetables` with IDs. */
function isLimitedTimetableApiPayload(data) {
    if (!data) return true;
    const raw = data.timetables;
    const rows = Array.isArray(raw) && raw.length > 0
        ? raw
        : (data.timetable ? [data.timetable] : []);
    if (rows.length > 1) return false;
    if (rows.length === 0) return true;
    const sid = rows[0].service_id;
    if (sid != null && String(sid).length > 0 && String(sid) !== 'unknown') {
        return false;
    }
    return true;
}

function updateTimetableSourceNotice(data) {
    const el = document.getElementById('timetable-source-notice');
    if (!el) return;
    if (isLimitedTimetableApiPayload(data)) {
        el.classList.remove('hidden');
        el.innerHTML =
            'The live API only returned <strong>one</strong> placeholder timetable (no per-train list). '
            + 'That is expected on the <strong>Cloudflare Workers</strong> deployment. '
            + 'For real multi-train NRDP times, run the repo&rsquo;s <strong>FastAPI</strong> backend (<code>api/app.py</code>) '
            + 'with <code>timetable_parsed.json</code> on the server and point the site at that API.';
    } else {
        el.classList.add('hidden');
        el.textContent = '';
    }
}

function formatTimeLabel(value) {
    if (!value) return '--:--';
    const date = typeof value === 'string' ? new Date(value) : value;
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
        return '--:--';
    }
    return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function formatDurationLabel(minutes) {
    const value = Number(minutes);
    if (!Number.isFinite(value)) return null;
    const totalMinutes = Math.round(value);
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    const parts = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (mins > 0) parts.push(`${mins}m`);
    if (parts.length === 0) parts.push('0m');
    return parts.join(' ');
}

function formatCurrency(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return '-';
    }
    return `£${Number(value).toFixed(2)}`;
}

function cleanConfidenceLabel(value) {
    if (!value) return 'N/A';
    if (typeof value === 'object' && value.value) {
        value = value.value;
    }
    if (typeof value === 'string') {
        const cleaned = value.split('.').pop();
        return cleaned.replace(/_/g, ' ');
    }
    return `${value}`;
}

function formatDelayLabel(minutes) {
    if (minutes === null || minutes === undefined || Number.isNaN(Number(minutes))) {
        return 'N/A';
    }
    return `${Math.round(Number(minutes))}m`;
}

function dedupeAndSortTimetables(list) {
    const seen = new Set();
    const out = [];
    for (const t of list) {
        const key = `${t.service_id}|${t.scheduled_departure}`;
        if (seen.has(key)) continue;
        seen.add(key);
        out.push(t);
    }
    out.sort((a, b) => {
        const da = new Date(a.scheduled_departure).getTime();
        const db = new Date(b.scheduled_departure).getTime();
        return da - db;
    });
    return out;
}

function minutesFromAnchor(timetable, anchorDate) {
    if (!timetable?.scheduled_departure || !anchorDate || Number.isNaN(anchorDate.getTime())) {
        return Infinity;
    }
    const dep = new Date(timetable.scheduled_departure);
    if (Number.isNaN(dep.getTime())) return Infinity;
    return Math.abs(dep.getTime() - anchorDate.getTime()) / 60000;
}

function getDisplayTimetableRows() {
    if (showAllServicesToday || !originalSearchAnchor || Number.isNaN(originalSearchAnchor.getTime())) {
        return { rows: [...sessionAllTimetables], relaxedWindow: false };
    }
    const filtered = sessionAllTimetables.filter((t) => {
        if (minutesFromAnchor(t, originalSearchAnchor) <= NEARBY_WINDOW_MINUTES) return true;
        return extraAnchorWindows.some(
            (a) => a && !Number.isNaN(a.getTime()) && minutesFromAnchor(t, a) <= NEARBY_WINDOW_MINUTES
        );
    });
    if (filtered.length === 0 && sessionAllTimetables.length > 0) {
        return { rows: [...sessionAllTimetables], relaxedWindow: true };
    }
    return { rows: filtered, relaxedWindow: false };
}

function updateScheduleFilterHint() {
    const el = document.getElementById('schedule-filter-hint');
    const btn = document.getElementById('toggle-schedule-scope');
    if (!el || !btn) return;
    const total = sessionAllTimetables.length;
    const { rows: displayRows, relaxedWindow } = getDisplayTimetableRows();
    const shown = displayRows.length;
    if (total === 0) {
        el.textContent = '';
        btn.classList.add('hidden');
        return;
    }
    btn.classList.remove('hidden');
    if (relaxedWindow) {
        el.textContent = `No departures fell in the ±${NEARBY_WINDOW_MINUTES} min window vs your time (often UTC vs local). Showing all ${total} loaded.`;
        btn.textContent = 'Show all services today';
    } else if (showAllServicesToday) {
        el.textContent = `Showing all ${total} service${total === 1 ? '' : 's'} for this route on this date.`;
        btn.textContent = `Show only ±${NEARBY_WINDOW_MINUTES} min`;
    } else {
        el.textContent = `Showing ${shown} near your search time (±${NEARBY_WINDOW_MINUTES} min per window; ${total} loaded).`;
        btn.textContent = 'Show all services today';
    }
}

function redrawTimetableCards() {
    const prediction = latestPredictionForCards;
    const fares = latestFaresForCards;
    const pagination = latestPagination;
    if (!prediction || sessionAllTimetables.length === 0) return;

    const { rows: displayList } = getDisplayTimetableRows();
    const originCode = document.getElementById('origin').value.toUpperCase();
    const destCode = document.getElementById('destination').value.toUpperCase();

    resultsList.innerHTML = '';
    updateScheduleFilterHint();

    if (displayList.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'bg-white border border-amber-200 rounded-xl p-5 text-slate-700 mb-4';
        empty.innerHTML = `
            <p class="font-medium text-slate-900">No trains in the current time windows</p>
            <p class="text-sm text-slate-600 mt-2">Try <strong>Show all services today</strong>, use &ldquo;Earlier / Later services&rdquo;, or change the departure time.</p>`;
        resultsList.appendChild(empty);
        if (pagination) addPaginationButtons(pagination);
        lucide.createIcons();
        return;
    }

    displayList.forEach((tt, index) => {
        const html = renderSingleService(tt, prediction, fares, originCode, destCode, index);
        const div = document.createElement('div');
        div.innerHTML = html;
        resultsList.appendChild(div);
    });

    if (pagination) addPaginationButtons(pagination);
    lucide.createIcons();
}

// --- Search Logic ---
searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const origin = document.getElementById('origin').value;
    const destination = document.getElementById('destination').value;
    const datetime = document.getElementById('datetime').value;

    if (!origin || !destination || !datetime) return;

    // UI Transition
    searchBtn.innerHTML = '<div class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>';
    searchBtn.disabled = true;

    try {
        const [date, time] = datetime.split('T');

        const response = await fetch(`${API_URL}/api/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                origin,
                destination,
                departure_date: date,
                departure_time: time,
                include_fares: true,
                use_cache: false
            }),
            mode: 'cors', // Explicitly enable CORS
            credentials: 'omit' // Don't send cookies
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error Response:', {
                status: response.status,
                statusText: response.statusText,
                url: response.url,
                body: errorText
            });
            throw new Error(`API Request Failed: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();

        // Transition to results view
        heroText.style.opacity = '0';
        heroText.style.height = '0';
        heroText.style.marginBottom = '0';
        heroText.style.overflow = 'hidden';

        mainContainer.classList.remove('justify-center', 'pb-24');
        mainContainer.classList.add('justify-start', 'pt-8');

        resultsContainer.classList.remove('hidden');

        // Update Header (only if this is the first result, or clear previous results)
        // Option: Clear previous results on new search
        resultsList.innerHTML = '';  // Clear previous results for new search

        document.getElementById('route-title').innerHTML = `${origin} <span class="text-slate-400 px-2">→</span> ${destination}`;
        document.getElementById('route-date').textContent = new Date(date).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });

        const payload = normalizeApiPayload(data);
        updateTimetableSourceNotice(payload);
        const anchorDate = new Date(`${date}T${time}`);
        renderResults(payload, false, { anchorDate });

    } catch (error) {
        console.error('Search error:', error);
        console.error('API_URL:', API_URL);
        console.error('API_BASE:', API_BASE);

        // Show more detailed error message
        let errorMessage = 'Search failed. ';
        if (error.message) {
            errorMessage += `Error: ${error.message}. `;
        }
        errorMessage += 'Please check the browser console for details.';
        alert(errorMessage);
    } finally {
        searchBtn.innerHTML = '<i data-lucide="search" class="w-5 h-5"></i>';
        searchBtn.disabled = false;
        lucide.createIcons();
    }
});

// State for pagination (already declared above at line 13-15)
// No need to redeclare - these variables are already defined in the State section

// Function to render a single service
function renderSingleService(timetable, prediction, fares, originCode, destCode, index) {
    const departureDateTime = timetable.scheduled_departure ? new Date(timetable.scheduled_departure) : null;
    const arrivalDateTime = timetable.scheduled_arrival ? new Date(timetable.scheduled_arrival) : null;
    const durationMinutes = Number(timetable.duration_minutes);

    const scheduledDepartureLabel = formatTimeLabel(departureDateTime);
    const scheduledArrivalLabel = formatTimeLabel(arrivalDateTime);
    const durationLabel = formatDurationLabel(durationMinutes);

    const delaySource = prediction.expected_delay_minutes ?? prediction.predicted_delay_minutes;
    const expectedDelayMinutes = Number.isFinite(Number(delaySource)) ? Number(delaySource) : null;
    const predictedArrival = arrivalDateTime && expectedDelayMinutes !== null
        ? new Date(arrivalDateTime.getTime() + expectedDelayMinutes * 60000)
        : null;
    const predictedArrivalLabel = formatTimeLabel(predictedArrival);
    const delayLabel = formatDelayLabel(expectedDelayMinutes);

    const onTimeProbability = typeof prediction.on_time_probability === 'number' ? prediction.on_time_probability : 0;
    const probabilityColor = onTimeProbability > 0.8 ? 'text-green-600' : (onTimeProbability > 0.6 ? 'text-yellow-600' : 'text-red-600');
    const ringColor = onTimeProbability > 0.8 ? '#16a34a' : (onTimeProbability > 0.6 ? '#ca8a04' : '#dc2626');
    const reliabilityLabel = onTimeProbability > 0.85 ? 'High' : (onTimeProbability > 0.6 ? 'Moderate' : 'Low');
    const confidenceLabel = cleanConfidenceLabel(prediction.confidence || prediction.confidence_level);
    const sampleSizeLabel = Number.isFinite(prediction.sample_size) ? prediction.sample_size.toLocaleString('en-GB') : 'N/A';

    const advanceLabel = formatCurrency(fares?.advance);
    const offPeakLabel = formatCurrency(fares?.off_peak);
    const anytimeLabel = formatCurrency(fares?.anytime);

    const cheapestTypeLabel = fares?.cheapest?.type ? fares.cheapest.type.replace(/_/g, ' ') : null;
    const hasCheapestPrice = fares?.cheapest && fares.cheapest.price !== null && fares.cheapest.price !== undefined;
    const cheapestPriceLabel = hasCheapestPrice ? formatCurrency(fares.cheapest.price) : null;
    const cheapestSummary = hasCheapestPrice ? `${(cheapestTypeLabel || 'Cheapest').toUpperCase()} • ${cheapestPriceLabel}` : 'Cheapest fare: -';

    const hasSavingsAmount = fares?.cheapest && fares.cheapest.savings_amount !== null && fares.cheapest.savings_amount !== undefined;
    const savingsSummary = hasSavingsAmount ? `Save ${formatCurrency(fares.cheapest.savings_amount)}${typeof fares.cheapest.savings_percentage === 'number' ? ` (${fares.cheapest.savings_percentage.toFixed(1)}%)` : ''}` : 'Savings: -';
    const fareFootnote = fares ? `Source: ${fares.meta?.data_source || 'NRDP'}${fares.meta?.cache_age_hours ? ` • Cached ${fares.meta.cache_age_hours}h ago` : ''}` : 'No fare data for this route yet.';

    const resultId = `service-${Date.now()}-${index}`;

    const serviceMetaParts = [];
    if (timetable?.service_id != null && timetable.service_id !== '') {
        serviceMetaParts.push(`ID ${timetable.service_id}`);
    }
    if (timetable?.route_type) {
        serviceMetaParts.push(String(timetable.route_type));
    }
    const serviceMetaLine = serviceMetaParts.length
        ? `<p class="text-[11px] text-slate-400 mt-1 font-mono">${serviceMetaParts.join(' · ')}</p>`
        : '';

    const html = `
        <div id="${resultId}" class="bg-white border border-slate-200 rounded-xl p-5 transition-all hover:border-blue-400 hover:shadow-md animate-fade-in mb-4">
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
                
                <!-- Timetable -->
                <div class="md:col-span-5 flex flex-col gap-4">
                    <div>
                        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Scheduled timetable</span>
                        <div class="flex items-center gap-3 text-2xl font-bold text-slate-900 mt-1">
                            <span>${scheduledDepartureLabel}</span>
                            <i data-lucide="arrow-right" class="w-4 h-4 text-slate-300"></i>
                            <span>${scheduledArrivalLabel}</span>
                        </div>
                        <p class="text-xs text-slate-500 mt-1">
                            ${durationLabel ? `Duration ${durationLabel}` : 'Duration: -'}
                            ${timetable?.service_frequency ? ` • ${timetable.service_frequency}` : ''}
                        </p>
                        ${serviceMetaLine}
                    </div>
                    <div class="rounded-lg bg-slate-50 px-3 py-2 flex flex-col gap-1 text-sm text-slate-600">
                        <div class="flex items-center justify-between">
                            <span>Predicted arrival</span>
                            <span class="text-base font-semibold text-slate-900">${predictedArrivalLabel}</span>
                        </div>
                        <div class="flex flex-wrap items-center gap-2 text-xs">
                            <span>Expected delay ${delayLabel}</span>
                            <span class="text-slate-300">•</span>
                            <span>Confidence ${confidenceLabel}</span>
                        </div>
                    </div>
                    <button id="${resultId}-toggle" class="mt-2 text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer">
                        <i data-lucide="chevron-down" class="w-3 h-3"></i>
                        <span>View intermediate stops</span>
                    </button>
                </div>

                <div class="md:col-span-3 flex flex-col gap-3 border-l-0 md:border-l border-slate-100 md:pl-6">
                    <div class="flex items-center gap-4">
                        <div class="relative flex items-center justify-center w-12 h-12">
                            <svg class="transform -rotate-90 w-12 h-12">
                                <circle class="text-slate-100" stroke-width="3" stroke="currentColor" fill="transparent" r="20" cx="24" cy="24"></circle>
                                <circle style="stroke: ${ringColor}; stroke-dasharray: ${2 * Math.PI * 20}; stroke-dashoffset: ${2 * Math.PI * 20 * (1 - onTimeProbability)}"
                                    stroke-width="3" stroke-linecap="round" fill="transparent" r="20" cx="24" cy="24"></circle>
                            </svg>
                            <span class="absolute text-[10px] font-bold text-slate-700">${(onTimeProbability * 100).toFixed(0)}%</span>
                        </div>
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">On-time chance</span>
                            <span class="text-sm font-bold ${probabilityColor}">${reliabilityLabel}</span>
                            <span class="text-xs text-slate-500">Sample size ${sampleSizeLabel}</span>
                        </div>
                    </div>
                </div>

                <div class="md:col-span-4 flex flex-col gap-4">
                    <div class="grid grid-cols-3 gap-3">
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">Advance</span>
                            <span class="text-xl font-bold text-slate-900">${advanceLabel}</span>
                        </div>
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">Off-Peak</span>
                            <span class="text-xl font-bold text-slate-900">${offPeakLabel}</span>
                        </div>
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">Anytime</span>
                            <span class="text-xl font-bold text-slate-900">${anytimeLabel}</span>
                        </div>
                    </div>
                    <div class="rounded-lg border border-slate-100 px-4 py-3 bg-slate-50/70">
                        <p class="text-sm font-semibold text-slate-900">${cheapestSummary}</p>
                        <p class="text-xs text-slate-500 mt-1">${savingsSummary}</p>
                    </div>
                    <p class="text-xs text-slate-400">${fareFootnote}</p>
                </div>

            </div>
            <div id="${resultId}-stops" class="hidden mt-4 pt-4 border-t border-slate-200">
                <div class="flex items-center gap-2 mb-3">
                    <i data-lucide="map-pin" class="w-4 h-4 text-slate-400"></i>
                    <span class="text-sm font-semibold text-slate-700">Intermediate Stops</span>
                </div>
                <div id="${resultId}-stops-content" class="text-sm text-slate-600">
                    <div class="flex items-center justify-center py-4">
                        <div class="w-5 h-5 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin"></div>
                        <span class="ml-2 text-slate-500">Loading...</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    return html;
}

function renderResults(data, append = false, options = {}) {
    if (!data || !data.prediction) {
        // Clear previous results if error
        resultsList.innerHTML = `
            <div class="bg-white border border-slate-200 rounded-xl p-5 text-slate-600">
                Unable to fetch prediction results. Please try again later.
            </div>
        `;
        return;
    }

    if (!append) {
        resultsList.innerHTML = '';
        currentTimetables = [];
        currentPagination = null;
        sessionAllTimetables = [];
        extraAnchorWindows = [];
        showAllServicesToday = false;
        originalSearchAnchor = null;
    }

    const prediction = data.prediction;
    const fares = data.fares || null;
    const timetables = data.timetables || (data.timetable ? [data.timetable] : []);
    const timetable = data.timetable || timetables[0] || null;
    const pagination = data.pagination || null;

    const datetimeInput = document.getElementById('datetime').value;

    if (!append) {
        currentSearchParams = {
            origin: document.getElementById('origin').value,
            destination: document.getElementById('destination').value,
            departure_date: document.getElementById('datetime').value.split('T')[0],
            departure_time: document.getElementById('datetime').value.split('T')[1]
        };
        originalSearchAnchor = options.anchorDate
            || (datetimeInput ? new Date(datetimeInput) : null);
    }
    if (append && options.anchorDate && !Number.isNaN(options.anchorDate.getTime())) {
        extraAnchorWindows.push(options.anchorDate);
    }

    currentPagination = pagination;

    if (timetables.length > 0) {
        if (!append) {
            sessionAllTimetables = dedupeAndSortTimetables(timetables);
        } else {
            sessionAllTimetables = dedupeAndSortTimetables([...sessionAllTimetables, ...timetables]);
        }
        currentTimetables = sessionAllTimetables;
        latestPredictionForCards = prediction;
        latestFaresForCards = fares;
        latestPagination = pagination;
        redrawTimetableCards();
        return;
    }

    const hintEl = document.getElementById('schedule-filter-hint');
    const scopeBtn = document.getElementById('toggle-schedule-scope');
    if (hintEl) hintEl.textContent = '';
    if (scopeBtn) scopeBtn.classList.add('hidden');

    const fallbackDeparture = datetimeInput ? new Date(datetimeInput) : null;

    const durationMinutes = Number(timetable?.duration_minutes);
    const scheduledDeparture = timetable?.scheduled_departure
        ? new Date(timetable.scheduled_departure)
        : fallbackDeparture;

    let scheduledArrival = timetable?.scheduled_arrival
        ? new Date(timetable.scheduled_arrival)
        : null;

    if (!scheduledArrival && scheduledDeparture && Number.isFinite(durationMinutes)) {
        scheduledArrival = new Date(scheduledDeparture.getTime() + durationMinutes * 60000);
    }

    const delaySource = prediction.expected_delay_minutes ?? prediction.predicted_delay_minutes;
    const expectedDelayMinutes = Number.isFinite(Number(delaySource))
        ? Number(delaySource)
        : null;

    const predictedArrival = scheduledArrival && expectedDelayMinutes !== null
        ? new Date(scheduledArrival.getTime() + expectedDelayMinutes * 60000)
        : null;

    const onTimeProbability = typeof prediction.on_time_probability === 'number'
        ? prediction.on_time_probability
        : 0;

    const probabilityColor = onTimeProbability > 0.8
        ? 'text-green-600'
        : (onTimeProbability > 0.6 ? 'text-yellow-600' : 'text-red-600');
    const ringColor = onTimeProbability > 0.8
        ? '#16a34a'
        : (onTimeProbability > 0.6 ? '#ca8a04' : '#dc2626');

    const reliabilityLabel = onTimeProbability > 0.85
        ? 'High'
        : (onTimeProbability > 0.6 ? 'Moderate' : 'Low');

    const confidenceLabel = cleanConfidenceLabel(
        prediction.confidence || prediction.confidence_level
    );
    const sampleSizeLabel = Number.isFinite(prediction.sample_size)
        ? prediction.sample_size.toLocaleString('en-GB')
        : 'N/A';

    const scheduledDepartureLabel = formatTimeLabel(scheduledDeparture);
    const scheduledArrivalLabel = formatTimeLabel(scheduledArrival);
    const predictedArrivalLabel = formatTimeLabel(predictedArrival);
    const durationLabel = formatDurationLabel(durationMinutes);
    const delayLabel = formatDelayLabel(expectedDelayMinutes);

    const advanceLabel = formatCurrency(fares?.advance);
    const offPeakLabel = formatCurrency(fares?.off_peak);
    const anytimeLabel = formatCurrency(fares?.anytime);

    const cheapestTypeLabel = fares?.cheapest?.type
        ? fares.cheapest.type.replace(/_/g, ' ')
        : null;
    const hasCheapestPrice = fares?.cheapest
        && fares.cheapest.price !== null
        && fares.cheapest.price !== undefined;
    const cheapestPriceLabel = hasCheapestPrice
        ? formatCurrency(fares.cheapest.price)
        : null;
    const cheapestSummary = hasCheapestPrice
        ? `${(cheapestTypeLabel || 'Cheapest').toUpperCase()} • ${cheapestPriceLabel}`
        : 'Cheapest fare: -';

    const hasSavingsAmount = fares?.cheapest
        && fares.cheapest.savings_amount !== null
        && fares.cheapest.savings_amount !== undefined;
    const savingsSummary = hasSavingsAmount
        ? `Save ${formatCurrency(fares.cheapest.savings_amount)}${typeof fares.cheapest.savings_percentage === 'number'
            ? ` (${fares.cheapest.savings_percentage.toFixed(1)}%)`
            : ''}`
        : 'Savings: -';

    const fareFootnote = fares
        ? `Source: ${fares.meta?.data_source || 'NRDP'}${fares.meta?.cache_age_hours ? ` • Cached ${fares.meta.cache_age_hours}h ago` : ''}`
        : 'No fare data for this route yet.';

    const onTimeStat = typeof timetable?.stats?.on_time_percentage === 'number'
        ? timetable.stats.on_time_percentage.toFixed(1)
        : null;
    const avgDelayStat = typeof timetable?.stats?.avg_delay_minutes === 'number'
        ? timetable.stats.avg_delay_minutes.toFixed(1)
        : null;
    const routeStatsLine = onTimeStat || avgDelayStat
        ? `Route stats: ${[
            onTimeStat ? `${onTimeStat}% on time` : null,
            avgDelayStat ? `avg delay ${avgDelayStat}m` : null
        ].filter(Boolean).join(' • ')}`
        : '';

    const originCode = document.getElementById('origin').value.toUpperCase();
    const destCode = document.getElementById('destination').value.toUpperCase();

    // Fallback: render single service (backward compatibility) - only if no timetables array
    const resultId = `result-${Date.now()}`;

    const html = `
        <div id="${resultId}" class="bg-white border border-slate-200 rounded-xl p-5 transition-all hover:border-blue-400 hover:shadow-md animate-fade-in">
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
                
                <!-- Timetable -->
                <div class="md:col-span-5 flex flex-col gap-4">
                    <div>
                        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Scheduled timetable</span>
                        <div class="flex items-center gap-3 text-2xl font-bold text-slate-900 mt-1">
                            <span>${scheduledDepartureLabel}</span>
                            <i data-lucide="arrow-right" class="w-4 h-4 text-slate-300"></i>
                            <span>${scheduledArrivalLabel}</span>
                        </div>
                        <p class="text-xs text-slate-500 mt-1">
                            ${durationLabel ? `Duration ${durationLabel}` : 'Duration: -'}
                            ${timetable?.service_frequency ? ` • ${timetable.service_frequency}` : ''}
                        </p>
                    </div>
                    <div class="rounded-lg bg-slate-50 px-3 py-2 flex flex-col gap-1 text-sm text-slate-600">
                        <div class="flex items-center justify-between">
                            <span>Predicted arrival</span>
                            <span class="text-base font-semibold text-slate-900">${predictedArrivalLabel}</span>
                        </div>
                        <div class="flex flex-wrap items-center gap-2 text-xs">
                            <span>Expected delay ${delayLabel}</span>
                            <span class="text-slate-300">•</span>
                            <span>Confidence ${confidenceLabel}</span>
                        </div>
                    </div>
                    <button id="${resultId}-toggle" class="mt-2 text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer">
                        <i data-lucide="chevron-down" class="w-3 h-3"></i>
                        <span>View intermediate stops</span>
                    </button>
                </div>

                <!-- Probability -->
                <div class="md:col-span-3 flex flex-col gap-3 border-l-0 md:border-l border-slate-100 md:pl-6">
                    <div class="flex items-center gap-4">
                        <div class="relative flex items-center justify-center w-12 h-12">
                            <svg class="transform -rotate-90 w-12 h-12">
                                <circle class="text-slate-100" stroke-width="3" stroke="currentColor" fill="transparent" r="20" cx="24" cy="24"></circle>
                                <circle style="stroke: ${ringColor}; stroke-dasharray: ${2 * Math.PI * 20}; stroke-dashoffset: ${2 * Math.PI * 20 * (1 - onTimeProbability)}"
                                    stroke-width="3" stroke-linecap="round" fill="transparent" r="20" cx="24" cy="24"></circle>
                            </svg>
                            <span class="absolute text-[10px] font-bold text-slate-700">${(onTimeProbability * 100).toFixed(0)}%</span>
                        </div>
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">On-time chance</span>
                            <span class="text-sm font-bold ${probabilityColor}">${reliabilityLabel}</span>
                            <span class="text-xs text-slate-500">Sample size ${sampleSizeLabel}</span>
                        </div>
                    </div>
                    ${routeStatsLine ? `<p class="text-xs text-slate-400">${routeStatsLine}</p>` : ''}
                </div>

                <!-- Fares -->
                <div class="md:col-span-4 flex flex-col gap-4">
                    <div class="grid grid-cols-3 gap-3">
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">Advance</span>
                            <span class="text-xl font-bold text-slate-900">${advanceLabel}</span>
                        </div>
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">Off-Peak</span>
                            <span class="text-xl font-bold text-slate-900">${offPeakLabel}</span>
                        </div>
                        <div class="flex flex-col gap-1">
                            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">Anytime</span>
                            <span class="text-xl font-bold text-slate-900">${anytimeLabel}</span>
                        </div>
                    </div>
                    <div class="rounded-lg border border-slate-100 px-4 py-3 bg-slate-50/70">
                        <p class="text-sm font-semibold text-slate-900">${cheapestSummary}</p>
                        <p class="text-xs text-slate-500 mt-1">${savingsSummary}</p>
                    </div>
                    <p class="text-xs text-slate-400">${fareFootnote}</p>
                </div>

            </div>
            <div id="${resultId}-stops" class="hidden mt-4 pt-4 border-t border-slate-200">
                <div class="flex items-center gap-2 mb-3">
                    <i data-lucide="map-pin" class="w-4 h-4 text-slate-400"></i>
                    <span class="text-sm font-semibold text-slate-700">Intermediate Stops</span>
                </div>
                <div id="${resultId}-stops-content" class="text-sm text-slate-600">
                    <div class="flex items-center justify-center py-4">
                        <div class="w-5 h-5 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin"></div>
                        <span class="ml-2 text-slate-500">加载中...</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Append instead of replace to allow multiple results
    const resultDiv = document.createElement('div');
    resultDiv.innerHTML = html;
    resultsList.appendChild(resultDiv);

    // Re-initialize lucide icons for the new content
    lucide.createIcons();

    // Add click handler for stops toggle - use setTimeout to ensure DOM is ready
    setTimeout(() => {
        const toggleBtn = document.getElementById(`${resultId}-toggle`);
        const stopsDiv = document.getElementById(`${resultId}-stops`);
        const stopsContent = document.getElementById(`${resultId}-stops-content`);

        if (!toggleBtn || !stopsDiv || !stopsContent) {
            console.error('Failed to find toggle elements:', { toggleBtn, stopsDiv, stopsContent });
            return;
        }

        let stopsLoaded = false;

        toggleBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            if (stopsDiv.classList.contains('hidden')) {
                stopsDiv.classList.remove('hidden');
                const icon = toggleBtn.querySelector('i');
                if (icon) {
                    icon.setAttribute('data-lucide', 'chevron-up');
                }

                if (!stopsLoaded) {
                    try {
                        const response = await fetch(`${API_URL}/api/routes/${originCode}/${destCode}/stops`, {
                            mode: 'cors',
                            credentials: 'omit'
                        });
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}`);
                        }
                        const stopsData = await response.json();

                        if (stopsData.stops && stopsData.stops.length > 0) {
                            let stopsHtml = '<div class="space-y-2">';
                            stopsData.stops.forEach((stop, index) => {
                                const depTime = stop.scheduled_departure
                                    ? formatTimeLabel(stop.scheduled_departure)
                                    : '-';
                                const arrTime = stop.scheduled_arrival
                                    ? formatTimeLabel(stop.scheduled_arrival)
                                    : '-';
                                const timeDisplay = depTime !== '-' ? depTime : (arrTime !== '-' ? arrTime : '-');

                                const isOrigin = stop.is_origin === true || index === 0;
                                const isDest = stop.is_destination === true || index === stopsData.stops.length - 1;

                                stopsHtml += `
                                    <div class="flex items-center gap-3 py-2 px-3 rounded-lg ${isOrigin || isDest ? 'bg-blue-50' : 'bg-slate-50'}">
                                        <div class="flex-shrink-0 w-16 text-xs font-mono text-slate-500">${timeDisplay}</div>
                                        <div class="flex-1">
                                            <div class="font-medium text-slate-900">${stop.location_name || stop.location}</div>
                                            <div class="text-xs text-slate-500">${stop.location}</div>
                                        </div>
                                        ${index < stopsData.stops.length - 1 ? '<i data-lucide="arrow-down" class="w-4 h-4 text-slate-300 flex-shrink-0"></i>' : ''}
                                    </div>
                                `;
                            });
                            stopsHtml += '</div>';
                            stopsContent.innerHTML = stopsHtml;
                        } else {
                            const message = stopsData.message || 'No intermediate stops data available';
                            stopsContent.innerHTML = `<p class="text-slate-500 text-center py-4">${message}</p>`;
                        }
                        stopsLoaded = true;
                    } catch (error) {
                        console.error('Failed to load stops:', error);
                        stopsContent.innerHTML = `<p class="text-red-500 text-center py-4">Failed to load: ${error.message}</p>`;
                    }
                    lucide.createIcons();
                }
            } else {
                stopsDiv.classList.add('hidden');
                const icon = toggleBtn.querySelector('i');
                if (icon) {
                    icon.setAttribute('data-lucide', 'chevron-down');
                }
            }
            lucide.createIcons();
        });
    }, 100);
}

// --- Pagination Functions ---
function addPaginationButtons(pagination) {
    // Remove existing pagination buttons if any
    const existingPagination = document.getElementById('pagination-buttons');
    if (existingPagination) {
        existingPagination.remove();
    }

    const paginationHtml = `
        <div id="pagination-buttons" class="flex flex-col gap-3 mt-6">
            ${pagination.has_more_earlier ? `
                <button id="load-earlier-btn" class="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-medium transition-colors flex items-center justify-center gap-2">
                    <i data-lucide="chevron-up" class="w-4 h-4"></i>
                    <span>View Earlier Services</span>
                </button>
            ` : ''}
            ${pagination.has_more_later ? `
                <button id="load-later-btn" class="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-medium transition-colors flex items-center justify-center gap-2">
                    <span>View Later Services</span>
                    <i data-lucide="chevron-down" class="w-4 h-4"></i>
                </button>
            ` : ''}
        </div>
    `;

    const paginationDiv = document.createElement('div');
    paginationDiv.innerHTML = paginationHtml;
    resultsList.appendChild(paginationDiv);

    lucide.createIcons();

    // Add event listeners
    setTimeout(() => {
        const earlierBtn = document.getElementById('load-earlier-btn');
        const laterBtn = document.getElementById('load-later-btn');

        if (earlierBtn) {
            earlierBtn.addEventListener('click', async () => {
                await loadMoreServices('earlier');
            });
        }

        if (laterBtn) {
            laterBtn.addEventListener('click', async () => {
                await loadMoreServices('later');
            });
        }
    }, 100);
}

function updatePaginationButtons(pagination) {
    const paginationDiv = document.getElementById('pagination-buttons');
    if (!paginationDiv) {
        addPaginationButtons(pagination);
        return;
    }

    // Update buttons based on pagination state
    const earlierBtn = document.getElementById('load-earlier-btn');
    const laterBtn = document.getElementById('load-later-btn');

    if (earlierBtn) {
        earlierBtn.style.display = pagination.has_more_earlier ? 'flex' : 'none';
    } else if (pagination.has_more_earlier) {
        const btn = document.createElement('button');
        btn.id = 'load-earlier-btn';
        btn.className = 'w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-medium transition-colors flex items-center justify-center gap-2';
        btn.innerHTML = '<i data-lucide="chevron-up" class="w-4 h-4"></i><span>View Earlier Services</span>';
        btn.addEventListener('click', async () => await loadMoreServices('earlier'));
        paginationDiv.insertBefore(btn, paginationDiv.firstChild);
    }

    if (laterBtn) {
        laterBtn.style.display = pagination.has_more_later ? 'flex' : 'none';
    } else if (pagination.has_more_later) {
        const btn = document.createElement('button');
        btn.id = 'load-later-btn';
        btn.className = 'w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-medium transition-colors flex items-center justify-center gap-2';
        btn.innerHTML = '<span>View Later Services</span><i data-lucide="chevron-down" class="w-4 h-4"></i>';
        btn.addEventListener('click', async () => await loadMoreServices('later'));
        paginationDiv.appendChild(btn);
    }

    lucide.createIcons();
}

async function loadMoreServices(direction) {
    if (!currentSearchParams || !currentPagination) return;

    const { origin, destination, departure_date, departure_time } = currentSearchParams;

    // Calculate new time based on direction
    const currentTime = new Date(`${departure_date}T${departure_time}:00`);
    const timeOffset = direction === 'earlier' ? -2 * 60 * 60 * 1000 : 2 * 60 * 60 * 1000; // ±2 hours
    const newTime = new Date(currentTime.getTime() + timeOffset);

    const newDate = newTime.toISOString().split('T')[0];
    const newTimeStr = newTime.toTimeString().split(':').slice(0, 2).join(':');

    try {
        const response = await fetch(`${API_URL}/api/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                origin,
                destination,
                departure_date: newDate,
                departure_time: newTimeStr,
                include_fares: true,
                use_cache: false
            }),
            mode: 'cors',
            credentials: 'omit'
        });

        if (!response.ok) {
            throw new Error(`API Request Failed: ${response.status}`);
        }

        const data = await response.json();
        const payload = normalizeApiPayload(data);
        updateTimetableSourceNotice(payload);

        // Append new results (anchor = time used for this request so ±2h window includes new batch)
        renderResults(payload, true, { anchorDate: newTime });
    } catch (error) {
        console.error('Failed to load more services:', error);
        alert(`Failed to load ${direction} services: ${error.message}`);
    }
}

// --- Initialization ---
window.addEventListener('DOMContentLoaded', async () => {
    initAnimation();

    // Load stations first, then setup autocomplete
    await loadStations();
    console.log('Stations loaded, setting up autocomplete...');

    setupAutocomplete('origin', 'origin-suggestions');
    setupAutocomplete('destination', 'destination-suggestions');

    // Default datetime
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('datetime').value = now.toISOString().slice(0, 16);

    document.getElementById('toggle-schedule-scope')?.addEventListener('click', () => {
        if (sessionAllTimetables.length === 0) return;
        showAllServicesToday = !showAllServicesToday;
        redrawTimetableCards();
    });

    console.log('Initialization complete');
});
