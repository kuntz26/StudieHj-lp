// Forhindrer lukning af dropdown-menu, når der klikkes inde i den
$(document).on("click", ".navbar-right .dropdown-menu", function (e) {
	e.stopPropagation();
});

// Tilføj interaktion med logoet (f.eks. klik på logoet fører til en specifik side)
$(document).on("click", ".navbar-brand .logo", function () {
	alert("Du klikkede på logoet!"); // Tilføj en handling her, f.eks. redirigering
	// window.location.href = "index.html"; // Eksempel: Naviger til hjemmesidens forside
});
