// Configuration
const apiBaseOverride =
    window.__RAILFAIR_API_BASE__ ||
    (document.documentElement && document.documentElement.dataset
        ? document.documentElement.dataset.apiBase
        : null);

const API_BASE = (apiBaseOverride || window.location.origin || '').replace(/\/+$/, '');
const API_URL = `${API_BASE}/api`;
const CANVAS_ID = 'rain-canvas';

// State
let stations = [];
let animationFrameId;

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
        const data = await response.json();
        stations = data.StationList;
    } catch (error) {
        console.error('Failed to load stations:', error);
        stations = [
            { crs: 'EUS', Value: 'London Euston' },
            { crs: 'MAN', Value: 'Manchester Piccadilly' }
        ];
    }
}

function setupAutocomplete(inputId, suggestionsId) {
    const input = document.getElementById(inputId);
    const suggestions = document.getElementById(suggestionsId);

    input.addEventListener('input', () => {
        const query = input.value.toLowerCase();
        if (query.length < 2) {
            suggestions.classList.add('hidden');
            return;
        }

        const matches = stations.filter(s =>
            s.Value.toLowerCase().includes(query) ||
            s.crs.toLowerCase().includes(query)
        ).slice(0, 8);

        suggestions.innerHTML = '';
        if (matches.length > 0) {
            matches.forEach(s => {
                const div = document.createElement('div');
                div.className = 'px-4 py-3 hover:bg-slate-50 cursor-pointer text-sm text-slate-700 border-b border-slate-50 last:border-0';
                div.textContent = `${s.Value} (${s.crs})`;
                div.onclick = () => {
                    input.value = s.crs;
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

        const response = await fetch(`${API_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin,
                destination,
                departure_date: date,
                departure_time: time,
                include_fares: true
            })
        });

        if (!response.ok) throw new Error('API Request Failed');
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
        renderResults(payload);

    } catch (error) {
        console.error(error);
        alert('Search failed. Please ensure the backend is running.');
    } finally {
        searchBtn.innerHTML = '<i data-lucide="search" class="w-5 h-5"></i>';
        searchBtn.disabled = false;
        lucide.createIcons();
    }
});

function renderResults(data) {
    if (!data || !data.prediction) {
        // Clear previous results if error
        resultsList.innerHTML = `
            <div class="bg-white border border-slate-200 rounded-xl p-5 text-slate-600">
                无法获取预测结果，请稍后重试。
            </div>
        `;
        return;
    }
    
    // Don't clear previous results - allow multiple queries
    // resultsList.innerHTML = ''; // Uncomment if you want to clear previous results

    const prediction = data.prediction;
    const fares = data.fares || null;
    const timetable = data.timetable || null;
    const datetimeInput = document.getElementById('datetime').value;
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
                        <span>查看中间站台</span>
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
                    <span class="text-sm font-semibold text-slate-700">中间站台</span>
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
                        const response = await fetch(`${API_URL}/routes/${originCode}/${destCode}/stops`);
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
                            stopsContent.innerHTML = '<p class="text-slate-500 text-center py-4">暂无中间站台数据</p>';
                        }
                        stopsLoaded = true;
                    } catch (error) {
                        console.error('Failed to load stops:', error);
                        stopsContent.innerHTML = `<p class="text-red-500 text-center py-4">加载失败: ${error.message}</p>`;
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

// --- Initialization ---
window.addEventListener('DOMContentLoaded', () => {
    initAnimation();
    loadStations();
    setupAutocomplete('origin', 'origin-suggestions');
    setupAutocomplete('destination', 'destination-suggestions');

    // Default datetime
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('datetime').value = now.toISOString().slice(0, 16);
});
