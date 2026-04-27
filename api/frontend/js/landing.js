// Landing page JS - scroll animations, nav effects, anonymous login
document.addEventListener("DOMContentLoaded", () => {
  // ── Scroll animations ──────────────────────────────────────────────────────
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) e.target.style.animationPlayState = "running";
    });
  }, { threshold: 0.1 });
  document.querySelectorAll(".animate-fade-up").forEach(el => {
    el.style.animationPlayState = "paused";
    observer.observe(el);
  });

  // ── Sticky nav ────────────────────────────────────────────────────────────
  const nav = document.querySelector(".nav");
  window.addEventListener("scroll", () => {
    nav.style.background = window.scrollY > 60 ? "rgba(13,15,26,0.9)" : "";
  });

  // ── If already logged-in, surface quick link ──────────────────────────────
  const token = localStorage.getItem("serenity_token");
  if (token) {
    document.querySelectorAll('a[href="/login.html"], a[href="/login.html#signup"]').forEach(btn => {
      if (btn.textContent.includes("Sign In") || btn.textContent.includes("Get Started")) {
        btn.href = "/chat.html";
        btn.textContent = "Open Serenity";
      }
    });
  }

  // ── Anonymous chat button ─────────────────────────────────────────────────
  // Convert all "Chat Anonymously" / "Try Anonymously" anchor tags to
  // buttons that first call /api/auth/anonymous, then redirect.
  document.querySelectorAll('a[href="/chat.html?anon=true"]').forEach(link => {
    link.addEventListener("click", async (e) => {
      e.preventDefault();
      const originalText = link.textContent;
      link.textContent = "Starting…";
      link.style.pointerEvents = "none";
      try {
        const res = await fetch("/api/auth/anonymous", { method: "POST" });
        if (!res.ok) throw new Error("Anonymous auth failed");
        const data = await res.json();
        localStorage.setItem("serenity_token", data.access_token);
        localStorage.setItem("serenity_user", JSON.stringify({
          username: data.username,
          user_id:  data.user_id,
          is_anonymous: true,
        }));
        window.location.href = "/chat.html?anon=true";
      } catch (err) {
        console.error("[Anon login]", err);
        link.textContent = originalText;
        link.style.pointerEvents = "";
        alert("Could not start anonymous session. Please try again.");
      }
    });
  });
});
