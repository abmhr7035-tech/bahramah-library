const search = document.getElementById("search");

search.addEventListener("input", function () {
    const value = this.value.trim().toLowerCase();

    document.querySelectorAll(".card").forEach(function(card) {
        card.style.display = card.textContent.toLowerCase().includes(value)
            ? ""
            : "none";
    });
});
