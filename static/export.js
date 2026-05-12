document.querySelector(".export-btn").addEventListener("click", () => {
  document.querySelector(".export-dropdown").classList.toggle("show");
});

// CSV export
document.querySelectorAll(".export-opt")[0].addEventListener("click", () => {
  window.location.href = "/export/csv";
});

// PDF export
document.querySelectorAll(".export-opt")[1].addEventListener("click", () => {
  window.location.href = "/export/pdf";
});