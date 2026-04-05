const revealItems = document.querySelectorAll(".section, .hero-panel .stat-card, .story-card, .fact-card, .solution-panel, .community-card, .response-card, .sources-card");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      }
    });
  },
  { threshold: 0.14 }
);

revealItems.forEach((item, index) => {
  item.classList.add("reveal");
  item.style.transitionDelay = `${Math.min(index * 50, 260)}ms`;
  observer.observe(item);
});

const contactForm = document.getElementById("contactForm");
const responseText = document.getElementById("responseText");
const submissionFeed = document.getElementById("submissionFeed");
const demandRange = document.getElementById("demandRange");
const heatRange = document.getElementById("heatRange");
const coolingSelect = document.getElementById("coolingSelect");

if (contactForm && responseText) {
  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = contactForm.querySelector("button[type='submit']");
    submitButton.disabled = true;
    submitButton.textContent = "Sending...";

    const formData = new FormData(contactForm);
    const payload = {
      name: formData.get("name"),
      email: formData.get("email"),
      interest: formData.get("interest"),
      message: formData.get("message"),
    };

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (!response.ok || !result.ok) {
        throw new Error(result.error || "Unable to send your message right now.");
      }

      responseText.textContent =
        `${payload.name}, your message was saved by the site backend. ${result.delivery}`;
      contactForm.reset();
      loadSubmissionFeed();
    } catch (error) {
      responseText.textContent = `Submission failed: ${error.message}`;
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Send interest";
    }
  });
}

async function loadSubmissionFeed() {
  if (!submissionFeed) {
    return;
  }

  try {
    const response = await fetch("/api/submissions");
    const result = await response.json();

    if (!response.ok) {
      throw new Error("Could not load recent submissions.");
    }

    if (!result.submissions || result.submissions.length === 0) {
      submissionFeed.innerHTML =
        '<p class="submission-empty">No public signals yet. The first stored submission will appear here in a privacy-safe format.</p>';
      return;
    }

    submissionFeed.innerHTML = result.submissions
      .map((submission) => {
        const date = new Date(submission.submittedAt).toLocaleDateString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
        });

        return `
          <article class="submission-item">
            <p class="update-label">${date}</p>
            <h4>${submission.name} reached out</h4>
            <p>Interest: ${submission.interest}</p>
          </article>
        `;
      })
      .join("");
  } catch (error) {
    submissionFeed.innerHTML =
      '<p class="submission-empty">Recent signals are unavailable right now.</p>';
  }
}

loadSubmissionFeed();

function updateSimulation() {
  if (!demandRange || !heatRange || !coolingSelect) {
    return;
  }

  const demand = Number(demandRange.value);
  const heat = Number(heatRange.value);
  const mode = coolingSelect.value;
  const coolingMultiplier = {
    evaporative: 1.25,
    hybrid: 0.85,
    closed: 0.42,
  }[mode];

  const waterPerHour = Math.round((600 + demand * 180 + heat * 140) * coolingMultiplier);
  const vaporIntensity = Math.min(0.25 + waterPerHour / 4000, 1);
  const activeChips = Math.min(8, Math.max(1, Math.round(demand * 0.8)));
  const heatScore = demand + heat;
  const bathtubEquivalent = Math.max(1, Math.round(waterPerHour / 200));

  document.getElementById("demandValue").textContent = `${demand} / 10`;
  document.getElementById("heatValue").textContent = `${heat} / 10`;
  document.getElementById("waterBar").style.width = `${Math.min(waterPerHour / 40, 100)}%`;
  document.getElementById("waterSourceLabel").textContent =
    mode === "closed"
      ? "Closed-loop systems reduce new water intake."
      : "Freshwater draw increases as cooling pressure rises.";
  document.getElementById("serverLabel").textContent =
    heatScore > 13
      ? "High compute demand is generating intense heat."
      : "Compute load is building heat inside the server hall.";
  document.getElementById("coolingLabel").textContent =
    mode === "evaporative"
      ? "Water evaporates to remove heat from the system."
      : mode === "hybrid"
        ? "The system mixes dry cooling with targeted water use."
        : "Liquid loops keep reusing coolant and reduce water loss.";

  document.getElementById("waterMetric").textContent = `${waterPerHour.toLocaleString()} liters / hour`;
  document.getElementById("waterMetricCopy").textContent =
    `Equivalent to roughly ${bathtubEquivalent} home bathtubs every hour in this illustration.`;
  document.getElementById("heatMetric").textContent =
    heatScore > 15 ? "Very high" : heatScore > 10 ? "High" : heatScore > 6 ? "Moderate" : "Lower";
  document.getElementById("heatMetricCopy").textContent =
    mode === "closed"
      ? "Closed-loop systems still manage heavy heat, but they lose less water on the way."
      : "More chips working harder means more heat that has to leave the building.";
  document.getElementById("awarenessMetric").textContent =
    mode === "evaporative"
      ? "Convenience can quietly turn into vapor."
      : mode === "hybrid"
        ? "Design choices can reduce the hidden burden."
        : "Better cooling design changes the public story.";
  document.getElementById("awarenessMetricCopy").textContent =
    mode === "closed"
      ? "People should know lower-water cooling pathways exist and deserve public pressure."
      : "People may only see faster AI tools, while local water systems absorb the strain.";

  document.getElementById("vaporCloud").style.opacity = `${vaporIntensity}`;
  document.getElementById("towerGlow").style.height = `${78 + heat * 5}px`;

  const chips = Array.from(document.querySelectorAll("#chipGrid .chip"));
  chips.forEach((chip, index) => {
    chip.classList.toggle("active", index < activeChips);
  });
}

[demandRange, heatRange, coolingSelect].forEach((control) => {
  if (control) {
    control.addEventListener("input", updateSimulation);
    control.addEventListener("change", updateSimulation);
  }
});

updateSimulation();
