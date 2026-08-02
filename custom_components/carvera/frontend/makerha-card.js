/**
 * MakerHA card - a single card showing a Makera Carvera CNC at a glance.
 *
 * Ships with the MakerHA integration and is registered automatically, so it
 * appears in the dashboard card picker as "Carvera (MakerHA)" with no
 * resource setup.
 */

const CARD_VERSION = "0.3.1";

console.info(
  `%c MAKERHA-CARD %c ${CARD_VERSION} `,
  "color: white; background: #2a78d6; font-weight: 700;",
  "color: #2a78d6; background: white; font-weight: 700;"
);

// entity_id suffix -> internal key. Entity ids are generated from the English
// entity names, so these are stable regardless of the user's HA language.
const SUFFIXES = {
  _state: "state",
  _online: "online",
  _alarm: "alarm",
  _spindle_speed: "spindle_speed",
  _spindle_temperature: "spindle_temp",
  _power_supply_temperature: "power_temp",
  _feed_rate: "feed",
  _tool: "tool",
  _target_tool: "target_tool",
  _job_progress: "progress",
  _job_file: "job_file",
  _job_elapsed: "elapsed",
  _job_playing: "playing",
  _controller_connected: "controller",
};

const STATES = {
  Idle: { icon: "mdi:check-circle", color: "var(--success-color, #0ca30c)" },
  Run: { icon: "mdi:play-circle", color: "var(--primary-color, #2a78d6)" },
  Home: { icon: "mdi:home-import-outline", color: "var(--primary-color, #2a78d6)" },
  Hold: { icon: "mdi:pause-circle", color: "var(--warning-color, #fab219)" },
  Pause: { icon: "mdi:pause-circle", color: "var(--warning-color, #fab219)" },
  Wait: { icon: "mdi:timer-sand", color: "var(--warning-color, #fab219)" },
  Tool: { icon: "mdi:tools", color: "var(--warning-color, #fab219)" },
  Alarm: { icon: "mdi:alert-circle", color: "var(--error-color, #d03b3b)" },
  Sleep: { icon: "mdi:sleep", color: "var(--disabled-text-color, #898781)" },
};

const OFFLINE = { icon: "mdi:power-plug-off", color: "var(--disabled-text-color, #898781)" };

/** 12% wash of a colour that also works when the colour is a CSS variable. */
const tint = (color) => `color-mix(in srgb, ${color} 12%, transparent)`;

const STYLES = `
  ha-card { padding: 16px; }
  .top { display: flex; align-items: center; gap: 14px; }
  .badge {
    width: 46px; height: 46px; border-radius: 12px; flex: 0 0 auto;
    display: flex; align-items: center; justify-content: center;
  }
  .badge ha-icon { --mdc-icon-size: 26px; }
  .headline { min-width: 0; }
  .state { font-size: 26px; font-weight: 600; line-height: 1.15; }
  .sub {
    font-size: 13px; color: var(--secondary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .clickable { cursor: pointer; }
  .callout {
    margin-top: 14px; padding: 10px 12px; border-radius: 10px;
    font-size: 15px; font-weight: 600;
    display: flex; align-items: center; gap: 8px;
  }
  .job { margin-top: 16px; }
  .jobline {
    display: flex; justify-content: space-between; align-items: baseline;
    gap: 12px; font-size: 13px; color: var(--secondary-text-color);
  }
  .jobfile {
    color: var(--primary-text-color); font-weight: 500;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .track {
    margin-top: 8px; height: 8px; border-radius: 4px; overflow: hidden;
    background: var(--divider-color, #e1e0d9);
  }
  .fill {
    height: 100%; border-radius: 4px 0 0 4px;
    background: var(--primary-color, #2a78d6);
    transition: width .6s ease;
  }
  .stats {
    margin-top: 18px; display: grid; gap: 12px 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .stat .label {
    font-size: 11px; text-transform: uppercase; letter-spacing: .04em;
    color: var(--secondary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .stat .value { font-size: 19px; font-weight: 600; margin-top: 2px; }
  .stat .value small { font-size: 12px; font-weight: 400; color: var(--secondary-text-color); }
  .dim { opacity: .5; }
  .warn { padding: 8px 0; color: var(--secondary-text-color); font-size: 14px; }
`;

class MakerHACard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  static getConfigElement() {
    return document.createElement("makerha-card-editor");
  }

  static getStubConfig(hass) {
    for (const entry of Object.values(hass?.entities ?? {})) {
      if (entry.platform === "carvera" && entry.device_id) {
        return { type: "custom:makerha-card", device_id: entry.device_id };
      }
    }
    return { type: "custom:makerha-card" };
  }

  setConfig(config) {
    this._config = config;
    this._entities = null;
  }

  getCardSize() {
    return 4;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  /** Map this device's entities to internal keys, once per config. */
  _resolve() {
    if (this._entities) return this._entities;
    const found = {};
    const registry = this._hass.entities ?? {};
    const deviceId = this._config?.device_id;
    for (const [entityId, entry] of Object.entries(registry)) {
      if (deviceId ? entry.device_id !== deviceId : entry.platform !== "carvera") continue;
      // longest match wins: "..._target_tool" also ends with "_tool", and which
      // one would claim the key otherwise depends on registry iteration order
      let best = null;
      for (const suffix of Object.keys(SUFFIXES)) {
        if (entityId.endsWith(suffix) && (best === null || suffix.length > best.length)) best = suffix;
      }
      if (best !== null && !found[SUFFIXES[best]]) found[SUFFIXES[best]] = entityId;
    }
    this._entities = found;
    return found;
  }

  _state(key) {
    const entityId = this._resolve()[key];
    return entityId ? this._hass.states[entityId] : undefined;
  }

  _num(key, digits = 0) {
    const st = this._state(key);
    if (!st || st.state === "unavailable" || st.state === "unknown") return null;
    const n = Number(st.state);
    return Number.isFinite(n) ? n.toFixed(digits) : null;
  }

  _unit(key) {
    return this._state(key)?.attributes?.unit_of_measurement ?? "";
  }

  _more(key) {
    const entityId = this._resolve()[key];
    if (!entityId) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      })
    );
  }

  _hms(seconds) {
    const s = Math.max(0, Number(seconds) | 0);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}:${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  }

  _statHtml(label, value, unit, key) {
    if (value === null || value === undefined) return "";
    const u = unit ? ` <small>${unit}</small>` : "";
    return `<div class="stat clickable" data-more="${key}">
      <div class="label">${label}</div><div class="value">${value}${u}</div>
    </div>`;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const ents = this._resolve();

    if (!ents.state) {
      this.shadowRoot.innerHTML = `<style>${STYLES}</style><ha-card><div class="warn">
        No Carvera device found. Pick one in the card editor, or check that the
        MakerHA integration is set up.</div></ha-card>`;
      return;
    }

    const stateObj = this._state("state");
    const onlineObj = this._state("online");
    const offline =
      (onlineObj && onlineObj.state === "off") ||
      !stateObj ||
      stateObj.state === "unavailable" ||
      stateObj.state === "unknown";

    const raw = offline ? "Offline" : stateObj.state;
    const look = offline ? OFFLINE : STATES[raw] ?? STATES.Idle;
    const label = offline
      ? "Offline"
      : this._hass.formatEntityState
        ? this._hass.formatEntityState(stateObj)
        : raw;

    const name =
      this._config.name ??
      this._hass.devices?.[this._config.device_id]?.name_by_user ??
      this._hass.devices?.[this._config.device_id]?.name ??
      stateObj.attributes.friendly_name?.replace(/\s+State$/i, "") ??
      "Carvera";

    // tool-change callout: the reason most people install this
    let callout = "";
    if (!offline && raw === "Tool") {
      const target = this._state("target_tool");
      const t = target && !isNaN(Number(target.state)) ? Number(target.state) : null;
      const text =
        t === null || t < 0 ? "Remove the tool, then press the button" : `Insert tool T${t}, then press the button`;
      callout = `<div class="callout" style="background:${tint(look.color)};color:${look.color}">
        <ha-icon icon="mdi:hand-back-right"></ha-icon><span>${text}</span></div>`;
    } else if (!offline && raw === "Alarm") {
      callout = `<div class="callout" style="background:${tint(look.color)};color:${look.color}">
        <ha-icon icon="mdi:alert"></ha-icon><span>Alarm - clear it before running a job</span></div>`;
    }

    // job block: shown while playing, or as the last job when idle
    const playing = this._state("playing")?.state === "on";
    const pct = Number(this._num("progress", 0) ?? 0);
    const file = this._state("job_file")?.state;
    const elapsed = this._state("elapsed")?.state;
    let job = "";
    if (!offline && (playing || (file && file !== "unknown" && file !== "unavailable"))) {
      const meta = [
        playing ? `${pct}%` : "last job",
        elapsed && !isNaN(Number(elapsed)) ? this._hms(elapsed) : null,
      ]
        .filter(Boolean)
        .join(" &middot; ");
      job = `<div class="job ${playing ? "" : "dim"}">
        <div class="jobline">
          <span class="jobfile clickable" data-more="job_file">${file ?? "job"}</span>
          <span>${meta}</span>
        </div>
        <div class="track"><div class="fill" style="width:${Math.min(100, Math.max(0, pct))}%"></div></div>
      </div>`;
    }

    const toolSt = this._state("tool");
    const toolVal =
      !toolSt || ["unknown", "unavailable"].includes(toolSt.state) ? null : `T${toolSt.state}`;

    const stats = [
      this._statHtml("Spindle", this._num("spindle_speed", 0), "rpm", "spindle_speed"),
      this._statHtml("Feed", this._num("feed", 0), this._unit("feed"), "feed"),
      this._statHtml("Tool", toolVal, "", "tool"),
      this._statHtml("Spindle temp", this._num("spindle_temp", 1), "°C", "spindle_temp"),
      this._statHtml("Power temp", this._num("power_temp", 1), "°C", "power_temp"),
    ].join("");

    this.shadowRoot.innerHTML = `<style>${STYLES}</style>
      <ha-card>
        <div class="top ${offline ? "dim" : ""}">
          <div class="badge" style="background:${tint(look.color)};color:${look.color}">
            <ha-icon icon="${look.icon}"></ha-icon>
          </div>
          <div class="headline">
            <div class="state clickable" data-more="state" style="color:${look.color}">${label}</div>
            <div class="sub">${name}</div>
          </div>
        </div>
        ${callout}
        ${job}
        <div class="stats ${offline ? "dim" : ""}">${stats}</div>
      </ha-card>`;

    this.shadowRoot.querySelectorAll("[data-more]").forEach((el) =>
      el.addEventListener("click", () => this._more(el.dataset.more))
    );
  }
}

const EDITOR_SCHEMA = [
  { name: "device_id", required: true, selector: { device: { integration: "carvera" } } },
  { name: "name", selector: { text: {} } },
];

class MakerHACardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) =>
        schema.name === "device_id" ? "Machine" : "Name (optional)";
      this._form.addEventListener("value-changed", (ev) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: { type: "custom:makerha-card", ...ev.detail.value } },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = this._config;
  }
}

customElements.define("makerha-card", MakerHACard);
customElements.define("makerha-card-editor", MakerHACardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "makerha-card",
  name: "Carvera (MakerHA)",
  description: "Machine state, tool changes, job progress and temperatures for a Makera Carvera CNC",
  preview: true,
  documentationURL: "https://github.com/BellionBastien/MakerHA",
});
