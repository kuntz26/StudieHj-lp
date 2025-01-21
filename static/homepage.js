// JavaScript til karussel-funktionalitet

const carousel = document.querySelector('.carousel');
const prevButton = document.querySelector('.prev');
const nextButton = document.querySelector('.next');

// Scroll til venstre
prevButton.addEventListener('click', () => {
    carousel.scrollBy({ left: -300, behavior: 'smooth' });
});

// Scroll til h�jre
nextButton.addEventListener('click', () => {
    carousel.scrollBy({ left: 300, behavior: 'smooth' });
});
