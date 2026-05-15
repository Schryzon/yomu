const CACHE_NAME = 'yomu-cache-v1';
const ASSETS = [
    '/',
    '/static/style.css',
    '/static/logo.png',
    'https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800;900&display=swap',
    'https://cdn.simpleicons.org/googlechrome/white',
    'https://cdn.simpleicons.org/firefoxbrowser/white',
    'https://cdn.simpleicons.org/apple/white',
    'https://cdn.simpleicons.org/github/white'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(ASSETS))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});
