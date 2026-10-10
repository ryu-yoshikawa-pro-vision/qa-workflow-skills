(() => {
  const params = new URLSearchParams(window.location.search);
  const knownViews = new Set(["overview", "search", "cart", "details", "confirmation"]);
  const initialView = knownViews.has(params.get("view")) ? params.get("view") : "overview";
  const state = { view: initialView, cart: [], delivery: "standard" };
  const views = [...document.querySelectorAll(".view")];
  const cartCount = document.querySelector("#cart-count");
  const cartItems = document.querySelector("#cart-items");
  const currentView = document.querySelector("#current-view");
  const journeyStatus = document.querySelector("#journey-status");
  const product = document.querySelector("#product");
  const textScale = document.querySelector("#text-scale");
  const textScaleValue = document.querySelector("#text-scale-value");
  const responsiveLayout = window.matchMedia("(max-width: 48rem)");

  if (params.get("alternate") === "1" || params.get("view") === "alternate") {
    document.body.classList.add("alternate-presentation");
  }

  function show(view, announcement) {
    state.view = view;
    for (const section of views) section.hidden = section.id !== `view-${view}`;
    currentView.textContent = view;
    if (announcement) journeyStatus.textContent = announcement;
  }

  function renderCart() {
    cartCount.textContent = String(state.cart.length);
    cartItems.replaceChildren();
    if (state.cart.length === 0) {
      const empty = document.createElement("li");
      empty.textContent = "Your cart is empty.";
      cartItems.append(empty);
      return;
    }
    for (const item of state.cart) {
      const row = document.createElement("li");
      row.textContent = item;
      cartItems.append(row);
    }
  }

  function resolveViewFromUrl() {
    const requested = new URL(window.location.href).searchParams.get("view");
    return knownViews.has(requested) ? requested : "overview";
  }

  for (const link of document.querySelectorAll(".site-header nav a[href*='view=']")) {
    link.addEventListener("click", (event) => {
      const destination = new URL(link.href);
      const view = destination.searchParams.get("view");
      if (!knownViews.has(view)) return;
      event.preventDefault();
      window.history.pushState({ fixtureView: view }, "", destination.href);
      show(view, `${view[0].toUpperCase()}${view.slice(1)} view opened.`);
    });
  }
  window.addEventListener("popstate", () => show(resolveViewFromUrl(), "Fixture navigation restored."));

  for (const button of document.querySelectorAll("[data-add]")) {
    button.addEventListener("click", () => {
      state.cart.push(button.dataset.add);
      renderCart();
      journeyStatus.textContent = `${button.dataset.add} added to the local fixture cart.`;
    });
  }
  document.querySelector("#start-journey").addEventListener("click", () => show("cart", "Checkout started. Shared page content remains unchanged."));
  document.querySelector("#search-add").addEventListener("click", () => {
    state.cart.push("Trail pack");
    renderCart();
    journeyStatus.textContent = "Trail pack added through the search route.";
  });
  document.querySelector("#product-search").addEventListener("input", (event) => {
    const query = event.target.value.trim();
    if (!query) {
      document.querySelector("#search-status").textContent = "Enter a product name to filter the fixture list.";
      return;
    }
    const found = "trail pack".includes(query.toLowerCase());
    document.querySelector("#search-status").textContent = found ? "Trail pack is available." : "No matching fixture product.";
  });
  document.querySelector("#continue-checkout").addEventListener("click", () => show("details", "Delivery details opened."));
  document.querySelector("#delivery-method").addEventListener("change", (event) => {
    state.delivery = event.target.value;
    document.querySelector("#delivery-summary").textContent = state.delivery;
  });
  document.querySelector("#place-order").addEventListener("click", () => {
    document.querySelector("#order-outcome").textContent = `The local fixture completed the journey with ${state.delivery} delivery. No order was sent.`;
    show("confirmation", "Journey complete. No external order was submitted.");
  });
  document.querySelector("#reset-journey").addEventListener("click", () => {
    state.cart = [];
    state.delivery = "standard";
    document.querySelector("#delivery-method").value = "standard";
    document.querySelector("#delivery-summary").textContent = "standard";
    renderCart();
    show("overview", "Fixture journey reset.");
  });
  document.querySelector("#high-contrast").addEventListener("click", (event) => {
    const enabled = product.dataset.theme !== "high-contrast";
    product.dataset.theme = enabled ? "high-contrast" : "standard";
    event.currentTarget.setAttribute("aria-pressed", String(enabled));
  });
  function applyTextScale() {
    const setting = Number(textScale.value);
    const renderedPercent = responsiveLayout.matches
      ? Math.min(200, 100 + (setting - 100) * 2)
      : setting;
    document.body.style.setProperty("--text-scale", String(renderedPercent / 100));
    textScaleValue.textContent = `${setting} setting; ${renderedPercent}% rendered`;
    textScale.setAttribute("aria-valuetext", `${renderedPercent}% rendered text scale`);
  }

  function syncTextScaleRange() {
    textScale.max = responsiveLayout.matches ? "150" : "200";
    if (Number(textScale.value) > Number(textScale.max)) textScale.value = textScale.max;
    applyTextScale();
  }

  textScale.addEventListener("input", applyTextScale);
  responsiveLayout.addEventListener("change", syncTextScaleRange);
  syncTextScaleRange();

  renderCart();
  show(initialView);
})();
