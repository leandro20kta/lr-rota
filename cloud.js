/* LR Rota — nuvem das viagens (Supabase REST, sem bibliotecas).
   Só guarda os DADOS da viagem (trajeto GPS, paragens, tempos): poucos KB. O vídeo 4K é gerado depois, no PC.
   Privacidade: cada pedido leva a "chave da nuvem" do utilizador (cabeçalho x-lr-key); a base de dados só mostra
   as viagens cujo dono tem o mesmo resumo (SHA-256) dessa chave. Sem a chave, ninguém lê nem apaga nada. */
(function(){
  const CFG = { url: 'https://lohyozmuwckdbqfbfyei.supabase.co', key: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxvaHlvem11d2NrZGJxZmJmeWVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMwMTMzMDAsImV4cCI6MjEwODU4OTMwMH0.405Gdyqgu-aU5YNrdmTtHU16_Y66_V3MUk9TD-AyEkI' };   // chave pública (anon): sem a chave pessoal x-lr-key não se lê nada
  const LS = 'lr.cloudKey';
  const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
  async function sha(s){ return hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))); }
  function newKey(){ const w = 'sol,mar,rio,ponte,serra,vale,lima,minho,rota,vila,porto,praia,monte,luz,estrada,curva'.split(','); const r = crypto.getRandomValues(new Uint32Array(5)); return [...r].map((v, i) => i < 4 ? w[v % w.length] : String(v % 10000).padStart(4, '0')).join('-'); }
  const api = {
    get configured(){ return !!(CFG.url && CFG.key); },
    myKey(){ return localStorage.getItem(LS) || ''; },
    setKey(k){ localStorage.setItem(LS, k.trim().toLowerCase()); },
    ensureKey(){ let k = api.myKey(); if(!k){ k = newKey(); api.setKey(k); } return k; },
    async req(path, opt = {}){
      if(!api.configured) throw new Error('A nuvem ainda não está ligada.');
      const k = api.myKey(); if(!k) throw new Error('Falta a chave da nuvem.');
      const r = await fetch(CFG.url + '/rest/v1/' + path, {...opt, headers: {apikey: CFG.key, Authorization: 'Bearer ' + CFG.key, 'Content-Type': 'application/json', 'x-lr-key': k, ...(opt.headers || {})}});
      if(!r.ok) throw new Error('Nuvem: ' + r.status + ' ' + (await r.text()).slice(0, 120));
      return r.status === 204 ? null : r.json();
    },
    async upload(name, km, data){ const owner = await sha(api.myKey()); return api.req('trips', {method: 'POST', headers: {Prefer: 'return=representation'}, body: JSON.stringify({owner_hash: owner, name, km, data})}); },
    async list(){ return api.req('trips?select=id,created_at,name,km&order=created_at.desc&limit=50'); },
    async get(id){ const r = await api.req('trips?select=data&id=eq.' + encodeURIComponent(id)); return r[0]?.data; },
    async remove(id){ return api.req('trips?id=eq.' + encodeURIComponent(id), {method: 'DELETE'}); }
  };
  window.LRCloud = api;
})();
