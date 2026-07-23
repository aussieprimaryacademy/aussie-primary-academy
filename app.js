const gradeSelect = document.getElementById("gradeSelect");
const subjectSelect = document.getElementById("subjectSelect");
const topicSelect = document.getElementById("topicSelect");
const acaraInput = document.getElementById("acaraInput");
const seedInput = document.getElementById("seedInput");
const worksheetPage = document.getElementById("worksheetPage");

const acaraDefaults = {
  "Mathematics": "AC9M1N01",
  "English Grammar & Literacy": "AC9E1LA01",
  "Science & EVS": "AC9S1U01"
};

function fillTopics() {
  const subject = subjectSelect.value;
  topicSelect.innerHTML = "";
  TOPICS[subject].forEach(topic => {
    const option = document.createElement("option");
    option.value = topic;
    option.textContent = topic;
    topicSelect.appendChild(option);
  });
  acaraInput.value = acaraDefaults[subject] || "";
}

function seededRandom(seed) {
  let value = Number(seed) || 101;
  return function () {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}

function pick(arr, rand) {
  return arr[Math.floor(rand() * arr.length)];
}

function buildQuestions(subject, topic, grade, seed) {
  const rand = seededRandom(seed);
  const base = SAMPLE_QUESTIONS[subject];

  return {
    a: [
      `${pick(base, rand)} Topic focus: ${topic}.`,
      `Write one thing you already know about ${topic}.`
    ],
    b: [
      `Complete this guided practice activity for ${topic}.`,
      `Answer carefully and use neat handwriting.`
    ],
    c: [
      `Apply your learning to a real classroom example about ${topic}.`,
      `Explain your thinking using words, numbers or pictures.`
    ],
    d: [
      `Challenge: Create your own ${topic} question for a friend.`,
      `High Five! Check your answer and colour the star when finished.`
    ]
  };
}

function renderSection(title, questions) {
  return `
    <section class="section-box">
      <div class="section-title">${title}</div>
      ${questions.map((question, index) => `
        <div class="question-line">${index + 1}. ${question}</div>
      `).join("")}
    </section>
  `;
}

function renderWorksheet() {
  const grade = gradeSelect.value;
  const subject = subjectSelect.value;
  const topic = topicSelect.value;
  const acara = acaraInput.value.trim();
  const seed = seedInput.value;
  const questions = buildQuestions(subject, topic, grade, seed);

  worksheetPage.innerHTML = `
    <header class="worksheet-header">
      <h2>${grade} ${topic} Worksheet</h2>
      <p>Aussie Primary Academy</p>
      <div class="meta-grid">
        <div class="meta-box"><strong>Grade:</strong><br>${grade}</div>
        <div class="meta-box"><strong>Subject:</strong><br>${subject}</div>
        <div class="meta-box"><strong>ACARA:</strong><br>${acara}</div>
      </div>
    </header>

    <section class="student-box">
      <div>Name: __________________________</div>
      <div>Date: __________________________</div>
    </section>

    <section class="info-box">
      <strong>Learning Intention:</strong>
      I can practise ${topic.toLowerCase()} skills and explain my thinking clearly.
      <br><br>
      <strong>Instructions:</strong>
      Complete each section from easy to challenging. Try your best and ask for help if needed.
    </section>

    ${renderSection("Section A: Warm Up", questions.a)}
    ${renderSection("Section B: Guided Practice", questions.b)}
    ${renderSection("Section C: Apply Your Learning", questions.c)}
    ${renderSection("Section D: Challenge", questions.d)}

    <section class="encouragement-box">
      ⭐ You're a star! Keep going and do your best work. High Five! ⭐
    </section>

    <section class="feedback-box">
      <strong>Teacher Feedback:</strong>
      <br><br>
      ________________________________________________________________
      <br>
      ________________________________________________________________
    </section>

    <footer class="footer-box">
      Website: aussieprimaryacademy.github.io/aussie-primary-academy<br>
      © 2026 Aussie Primary Academy. All Rights Reserved.<br>
      Original Content - For Educational Use Only. Redistribution Prohibited.
    </footer>
  `;
}

subjectSelect.addEventListener("change", () => {
  fillTopics();
  renderWorksheet();
});

gradeSelect.addEventListener("change", renderWorksheet);
topicSelect.addEventListener("change", renderWorksheet);
acaraInput.addEventListener("input", renderWorksheet);
seedInput.addEventListener("input", renderWorksheet);

document.getElementById("generateBtn").addEventListener("click", renderWorksheet);

document.getElementById("randomBtn").addEventListener("click", () => {
  seedInput.value = Math.floor(Math.random() * 99999) + 1;
  renderWorksheet();
});

document.getElementById("printBtn").addEventListener("click", () => window.print());

fillTopics();
renderWorksheet();const gradeSelect = document.getElementById("gradeSelect");
const subjectSelect = document.getElementById("subjectSelect");
const topicSelect = document.getElementById("topicSelect");
const acaraInput = document.getElementById("acaraInput");
const seedInput = document.getElementById("seedInput");
const worksheetPage = document.getElementById("worksheetPage");

const acaraDefaults = {
  "Mathematics": "AC9M1N01",
  "English Grammar & Literacy": "AC9E1LA01",
  "Science & EVS": "AC9S1U01"
};

function fillTopics() {
  const subject = subjectSelect.value;
  topicSelect.innerHTML = "";
  TOPICS[subject].forEach(topic => {
    const option = document.createElement("option");
    option.value = topic;
    option.textContent = topic;
    topicSelect.appendChild(option);
  });
  acaraInput.value = acaraDefaults[subject] || "";
}

function seededRandom(seed) {
  let value = Number(seed) || 101;
  return function () {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}

function pick(arr, rand) {
  return arr[Math.floor(rand() * arr.length)];
}

function buildQuestions(subject, topic, grade, seed) {
  const rand = seededRandom(seed);
  const base = SAMPLE_QUESTIONS[subject];

  return {
    a: [
      `${pick(base, rand)} Topic focus: ${topic}.`,
      `Write one thing you already know about ${topic}.`
    ],
    b: [
      `Complete this guided practice activity for ${topic}.`,
      `Answer carefully and use neat handwriting.`
    ],
    c: [
      `Apply your learning to a real classroom example about ${topic}.`,
      `Explain your thinking using words, numbers or pictures.`
    ],
    d: [
      `Challenge: Create your own ${topic} question for a friend.`,
      `High Five! Check your answer and colour the star when finished.`
    ]
  };
}

function renderSection(title, questions) {
  return `
    <section class="section-box">
      <div class="section-title">${title}</div>
      ${questions.map((question, index) => `
        <div class="question-line">${index + 1}. ${question}</div>
      `).join("")}
    </section>
  `;
}

function renderWorksheet() {
  const grade = gradeSelect.value;
  const subject = subjectSelect.value;
  const topic = topicSelect.value;
  const acara = acaraInput.value.trim();
  const seed = seedInput.value;
  const questions = buildQuestions(subject, topic, grade, seed);

  worksheetPage.innerHTML = `
    <header class="worksheet-header">
      <h2>${grade} ${topic} Worksheet</h2>
      <p>Aussie Primary Academy</p>
      <div class="meta-grid">
        <div class="meta-box"><strong>Grade:</strong><br>${grade}</div>
        <div class="meta-box"><strong>Subject:</strong><br>${subject}</div>
        <div class="meta-box"><strong>ACARA:</strong><br>${acara}</div>
      </div>
    </header>

    <section class="student-box">
      <div>Name: __________________________</div>
      <div>Date: __________________________</div>
    </section>

    <section class="info-box">
      <strong>Learning Intention:</strong>
      I can practise ${topic.toLowerCase()} skills and explain my thinking clearly.
      <br><br>
      <strong>Instructions:</strong>
      Complete each section from easy to challenging. Try your best and ask for help if needed.
    </section>

    ${renderSection("Section A: Warm Up", questions.a)}
    ${renderSection("Section B: Guided Practice", questions.b)}
    ${renderSection("Section C: Apply Your Learning", questions.c)}
    ${renderSection("Section D: Challenge", questions.d)}

    <section class="encouragement-box">
      ⭐ You're a star! Keep going and do your best work. High Five! ⭐
    </section>

    <section class="feedback-box">
      <strong>Teacher Feedback:</strong>
      <br><br>
      ________________________________________________________________
      <br>
      ________________________________________________________________
    </section>

    <footer class="footer-box">
      Website: aussieprimaryacademy.github.io/aussie-primary-academy<br>
      © 2026 Aussie Primary Academy. All Rights Reserved.<br>
      Original Content - For Educational Use Only. Redistribution Prohibited.
    </footer>
  `;
}

subjectSelect.addEventListener("change", () => {
  fillTopics();
  renderWorksheet();
});

gradeSelect.addEventListener("change", renderWorksheet);
topicSelect.addEventListener("change", renderWorksheet);
acaraInput.addEventListener("input", renderWorksheet);
seedInput.addEventListener("input", renderWorksheet);

document.getElementById("generateBtn").addEventListener("click", renderWorksheet);

document.getElementById("randomBtn").addEventListener("click", () => {
  seedInput.value = Math.floor(Math.random() * 99999) + 1;
  renderWorksheet();
});

document.getElementById("printBtn").addEventListener("click", () => window.print());

fillTopics();
renderWorksheet();