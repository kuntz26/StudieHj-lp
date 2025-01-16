// Forhindrer lukning af dropdown-menu, n�r der klikkes inde i den
$(document).on("click", ".navbar-right .dropdown-menu", function (e) {
	e.stopPropagation();
});

// Tilf�j interaktion med logoet (f.eks. klik p� logoet f�rer til en specifik side)
$(document).on("click", ".navbar-brand .logo", function () {
	alert("Du klikkede p� logoet!"); // Tilf�j en handling her, f.eks. redirigering
	// window.location.href = "index.html"; // Eksempel: Naviger til hjemmesidens forside
});
