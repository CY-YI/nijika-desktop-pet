"use strict";

// Keep the submitted snapshot separate from edits made during a pending save.
class FormDraft {
  constructor(form, status, onChange = () => {}) {
    this.form = form;
    this.status = status;
    this.onChange = onChange;
    this.baseline = null;
    this.saving = false;
    this.error = "";
    this.idleMessage = status.textContent;
    for (const event of ["input", "change"]) {
      form.addEventListener(event, () => {
        this.error = "";
        this.render();
      });
    }
    this.render();
  }

  values() {
    const values = {};
    for (const field of this.form.elements) {
      const key = field.name || field.id;
      if (!key || !["INPUT", "SELECT", "TEXTAREA"].includes(field.tagName) ||
          ["file", "submit", "button"].includes(field.type)) continue;
      if (field.type === "radio" && !field.checked) continue;
      values[key] = field.type === "checkbox" ? field.checked : field.value;
    }
    return values;
  }

  get dirty() {
    return this.baseline !== null &&
      JSON.stringify(this.values()) !== JSON.stringify(this.baseline);
  }

  sync(write, message = this.idleMessage) {
    this.idleMessage = message;
    if (!this.dirty && !this.saving) {
      write();
      this.baseline = this.values();
    }
    this.render();
  }

  render() {
    const dirty = this.dirty;
    this.form.dataset.saveState = this.error ? "error" : this.saving ? "saving" : dirty ? "dirty" : "saved";
    this.form.setAttribute("aria-busy", String(this.saving));
    const message = this.error ? "未能保存：" + this.error
      : this.saving ? "正在保存，仍可继续修改…"
      : dirty ? "有未保存的修改" : this.idleMessage;
    if (this.status.textContent !== message) this.status.textContent = message;
    this.form.querySelector('[type="submit"]').disabled = this.baseline === null || !dirty || this.saving;
    this.onChange();
  }

  async save(write) {
    if (this.saving || !this.dirty) return false;
    const submitted = this.values();
    this.saving = true;
    this.error = "";
    this.render();
    try {
      await write(submitted);
      this.baseline = submitted;
      return true;
    } catch (error) {
      this.error = error.message || "请重试。";
      throw error;
    } finally {
      this.saving = false;
      this.render();
    }
  }
}
