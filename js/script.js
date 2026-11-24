const search = document.getElementById("search");
const newsCards = document.querySelectorAll(".news-card");

search.addEventListener("input", function () {
    const value = this.value.trim().toLowerCase();

    newsCards.forEach(function (card) {
        const text = card.textContent.toLowerCase();

        card.style.display = text.includes(value) ? "" : "none";
    });
});
