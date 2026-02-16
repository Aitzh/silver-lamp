import fetch from "node-fetch";

async function getAccessToken() {
    const auth = Buffer.from(`${process.env.SPOTIFY_CLIENT_ID}:${process.env.SPOTIFY_CLIENT_SECRET}`).toString('base64');
    const res = await fetch('https://accounts.spotify.com/api/token', {
        method: 'POST',
        headers: { 'Authorization': `Basic ${auth}`, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'grant_type=client_credentials'
    });
    const data = await res.json();
    return data.access_token;
}

export async function searchTracks(genre, offset = 0) {
    const token = await getAccessToken();
    const url = `https://api.spotify.com/v1/search?q=genre:${genre}&type=track&limit=12&offset=${offset}`;

    const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json();

    return (data.tracks?.items || []).map(t => ({
        id: t.id,
        title: t.name,
        artist: t.artists.map(a => a.name).join(", "),
        image: t.album.images[0]?.url,
        duration: `${Math.floor(t.duration_ms / 60000)}:${((t.duration_ms % 60000) / 1000).toFixed(0).padStart(2, '0')}`
    }));
}