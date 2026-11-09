(() => {
  const toggle = document.querySelector("[data-nav-toggle]");
  const menu = document.querySelector("[data-nav-menu]");

  if (!toggle || !menu) return;

  toggle.addEventListener("click", () => {
    const isOpen = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!isOpen));
    menu.classList.toggle("is-open", !isOpen);
  });
})();


document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    if (!target) return;
    const value = target.textContent.trim();
    try {
      await navigator.clipboard.writeText(value);
      const original = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => { button.textContent = original; }, 1800);
    } catch (_) {
      button.textContent = "Select and copy";
    }
  });
});


// Show the relevant academic assignment fields for the selected account role.
(() => {
  const role = document.getElementById("id_role");
  const groups = document.querySelectorAll("[data-role-field]");
  if (!role || !groups.length) return;
  const update = () => {
    groups.forEach((group) => {
      const visible = group.dataset.roleField === role.value;
      group.hidden = !visible;
      group.querySelectorAll("input, select, textarea").forEach((field) => {
        field.disabled = !visible;
      });
    });
  };
  role.addEventListener("change", update);
  update();
})();
