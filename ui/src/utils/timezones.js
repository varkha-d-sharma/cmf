/***
 * Copyright (2026) Hewlett Packard Enterprise Development LP
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * You may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ***/

// Utilities to build a dynamic list of IANA time zones with UTC offsets
// alias mapping
const TIMEZONE_ALIASES = {
  "Asia/Calcutta": "Asia/Kolkata",
  "Asia/Katmandu": "Asia/Kathmandu",
  "Asia/Saigon": "Asia/Ho_Chi_Minh", // added
};

// Normalizing old or non-standard time zone names to their modern IANA equivalents
function normalizeTimeZone(tz) {
  return TIMEZONE_ALIASES[tz] || tz;
}

// Get a list of supported time zones from the environment, with a fallback if not available
function supportedTimeZones() {
  // Intl is a modern API that provides a list of supported time zones, but it may not be available in all environments
  if (typeof Intl !== 'undefined' && typeof Intl.supportedValuesOf === 'function') {
    try {
      // returns an array of all timezone identifiers that the browser supports.
      const zones = Intl.supportedValuesOf('timeZone');
      if (Array.isArray(zones) && zones.length) return zones;
    } catch (_) { /* ignore */ }
  }
  // Minimal fallback: include UTC and the user's local zone if available
  const local = getLocalTimeZone();
  const set = new Set(["UTC"]);
  if (local) set.add(local);
  return Array.from(set);
}

// Get the user's local time zone or default to 'UTC'
export function getLocalTimeZone() {
  try {
    // Get user's browser timezone, fallback to UTC if unavailable
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    return normalizeTimeZone(tz);
  } catch (_) {
    return 'UTC';
  }
}

// Calculate the UTC offset in minutes for a given time zone and date (defaulting to now)
// For eg: Asia/Kolkata is UTC+05:30, which is 330 minutes from UTC.
function getOffsetMinutes(tz, date = new Date()) {
  // Create a formatter that converts the given UTC date into the target timezone.
  // Example: UTC 12:00 → Asia/Kolkata becomes 17:30
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,        // Convert time into "Asia/Kolkata"
    year: 'numeric',     // e.g. "2026"
    month: '2-digit',    // e.g. "04"
    day: '2-digit',      // e.g. "01"
    hour: '2-digit',     // e.g. "17" (5 PM in 24-hour format)
    minute: '2-digit',   // e.g. "30"
    second: '2-digit',   // e.g. "00"
    hour12: false,       // Use 24-hour format (no AM/PM)
    hourCycle: 'h23'     // Keep hours between 00–23
  });

  // Break the formatted date into parts (structured format)
  const parts = fmt.formatToParts(date);

  // Convert parts into a clean object
  // Example: { year: "2026", month: "04", day: "01", hour: "17", minute: "30", second: "00" }
  const values = Object.fromEntries(
    parts
      .filter((part) => part.type !== 'literal') // Remove separators like "/", ":", ","
      .map((part) => [part.type, part.value])    // Keep only useful data
  );

  // Now we create a UTC timestamp from the timezone-adjusted values
  // We treat "17:30" as if it is UTC time
  // Example: Date.UTC(2026, 3, 1, 17, 30, 0) → timestamp for 17:30 UTC
  const zonedUtcMs = Date.UTC(
    Number(values.year),         // 2026
    Number(values.month) - 1,    // JS months are 0-based → April = 3
    Number(values.day),          // 1
    Number(values.hour),         // 17
    Number(values.minute),       // 30
    Number(values.second)        // 0
  );

  // Original timestamp:
  // date.getTime() = 12:00 UTC
  // zonedUtcMs: 17:30 UTC (but actually represents Asia/Kolkata time)
  // Difference: 17:30 - 12:00 = 5 hours 30 minutes = 330 minutes
  const offset = Math.round(
    (zonedUtcMs - date.getTime()) / 60000 // Convert milliseconds → minutes
  );

  // Handle edge case: avoid returning -0
  // If offset is 0 or -0 → return clean 0
  return offset === 0 ? 0 : offset;
}

// Format the offset in minutes into a human-readable string like "UTC+05:30" or "UTC-04:00"
function formatOffsetLabel(offsetMinutes) {
  const sign = offsetMinutes >= 0 ? '+' : '-';
  const absoluteMinutes = Math.abs(offsetMinutes);
  const hours = String(Math.floor(absoluteMinutes / 60)).padStart(2, '0');
  const minutes = String(absoluteMinutes % 60).padStart(2, '0');
  return `UTC${sign}${hours}:${minutes}`;
}

// Build a list of time zone options with offsets for UI dropdowns
export function buildTimeZoneOptions() {
  // Get supported time zones
  const zones = supportedTimeZones();
  // Map each time zone to an object with value, label, group, and offset info
  // for eg: { value: "America/New_York", label: "UTC-05:00 — America/New_York", group: "America", offset: "UTC-05:00", offsetMinutes: -300 }
  const items = zones.map(z => {
    const tz = normalizeTimeZone(z);

    const group = tz.includes('/') ? tz.split('/')[0] : 'Other';
    let offsetMinutes = 0;
    let offset = 'UTC+00:00';

    // Calculate the offset in minutes and format it, but if it fails (e.g. invalid tz), fallback to just getting the label
    try {
      offsetMinutes = getOffsetMinutes(tz);
      offset = formatOffsetLabel(offsetMinutes);
    } catch (_) {
      offsetMinutes = 0;
      offset = 'UTC+00:00';
    }

    return {
      value: tz,
      label: `${offset} — ${tz}`,
      group,
      offset,
      offsetMinutes
    };
  });

  // Remove duplicates by using a Map keyed by the time zone value (e.g. "America/New_York")
  const uniqueMap = new Map();
  items.forEach(item => uniqueMap.set(item.value, item));

  const uniqueItems = Array.from(uniqueMap.values());

  // Sort: First by offsetMinutes (e.g. -300 for UTC-05:00), then alphabetically by value to ensure consistent order for time zones with the same offset
  uniqueItems.sort(
    (a, b) => a.offsetMinutes - b.offsetMinutes || a.value.localeCompare(b.value)
  );

  // Eg: [ { value: "America/New_York", label: "UTC-05:00 — America/New_York", group: "America", offset: "UTC-05:00", offsetMinutes: -300 }, ... ]
  return uniqueItems;
}