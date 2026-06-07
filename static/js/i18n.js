/* Rotaka — i18n translation layer */

const TRANSLATIONS = {
  tr: {
    /* nav */
    'nav.home':      'Ana Sayfa',
    'nav.play':      'Oyna',
    'nav.spectate':  'İzle',
    'nav.vscomp':    'Bilgisayara Karşı',
    'nav.profile':   'Profil',
    'nav.login':     'Giriş Yap',
    'nav.register':  'Kayıt Ol',
    'nav.logout':    'Çıkış Yap',

    /* lobby */
    'lobby.title':      '⬡ ROTAKA ⬡',
    'lobby.subtitle':   'Çevrimiçi Çok Oyunculu',
    'lobby.create':     'Oda Oluştur  (Beyaz Ol)',
    'lobby.join':       'Odaya Katıl',
    'lobby.join_ph':    'Oda kodu gir…',
    'lobby.join_btn':   'Katıl',
    'lobby.or':         '— ya da —',
    'lobby.waiting':    'Rakip bekleniyor…',
    'lobby.room_code':  'Oda Kodun:',
    'lobby.room_hint':  'Bu kodu arkadaşına gönder',
    'lobby.live':       'Canlı Maçlar',
    'lobby.no_live':    'Şu an canlı maç yok.',
    'lobby.watch':      'İzle',
    'lobby.moves':      'Hamle',

    /* game */
    'game.your_turn':   'Senin Sıran',
    'game.opp_turn':    'Rakip Düşünüyor…',
    'game.boost':       '⚡ BOOST',
    'game.you':         'SEN',
    'game.white':       'BEYAZ',
    'game.black':       'SİYAH',
    'game.move':        'Hamle',
    'game.inf_top':     "Siyah'ın Evi",
    'game.inf_bot':     "Beyaz'ın Evi",
    'game.repeat':      'Tekrar',
    'game.inactive':    'Eylemsiz',
    'game.notation':    'Hamle Notasyonu',
    'game.chat':        'Sohbet',
    'game.chat_ph':     'Mesaj yaz…',
    'game.send':        'Gönder',
    'game.swap_title':  '👑 PIE RULE',
    'game.swap_desc':   'Beyazın ilk hamlesini gördünüz. Rolleri değiştirmek ister misiniz?',
    'game.swap_keep':   'Siyah Olarak Kal',
    'game.swap_do':     '⇄ ROLLERİ DEĞİŞTİR (SWAP)',
    'game.swap_wait':   '⏳ Rakip Pie Rule kararını veriyor…',
    'game.over':        'Oyun Bitti!',
    'game.lobby':       'Lobiye Dön',
    'game.elo_change':  'ELO Değişimi',
    'game.opp_left':    'Rakip Ayrıldı',
    'game.opp_left_msg':'Rakibiniz oyundan çıktı.',

    /* profile */
    'profile.stats':    'İstatistikler',
    'profile.games':    'Toplam Oyun',
    'profile.wins':     'Galibiyet',
    'profile.losses':   'Mağlubiyet',
    'profile.draws':    'Beraberlik',
    'profile.winpct':   'Kazanma %',
    'profile.inf_wins': 'İşgalle Kazanma',
    'profile.elim_wins':'Taş İmhasıyla Kazanma',
    'profile.history':  'Son Oyunlar',
    'profile.friends':  'Arkadaşlar',
    'profile.add_friend':'Arkadaş Ekle',
    'profile.friend_sent':'İstek Gönderildi',
    'profile.accept':   'Kabul Et',
    'profile.rank':     'Rütbe',
    'profile.elo':      'ELO',
    'profile.no_games': 'Henüz oyun yok.',
    'profile.no_friends':'Henüz arkadaş yok.',

    /* auth */
    'login.title':      'Giriş Yap',
    'login.username':   'Kullanıcı Adı',
    'login.password':   'Şifre',
    'login.submit':     'Giriş Yap',
    'login.no_acc':     'Hesabın yok mu?',
    'login.register':   'Kayıt Ol',
    'login.google':     'Google ile Giriş Yap',
    'register.title':   'Kayıt Ol',
    'register.submit':  'Hesap Oluştur',
    'register.have_acc':'Zaten hesabın var mı?',

    /* vs computer */
    'vscomp.title':     'Bilgisayara Karşı Oyna',
    'vscomp.coming':    'Yakında…',
    'vscomp.desc':      'Eğitilmiş Rotaka AI\'larımız bu sayfaya eklenecek. Şu an sadece çevrimiçi oyun mevcut.',

    /* spectate */
    'spectate.title':   'Canlı Maçlar',
    'spectate.none':    'Şu an canlı maç bulunmuyor.',
    'spectate.watch':   'İzle',
    'spectate.moves':   'hamle',

    /* ranks */
    'rank.bronz':   'Bronz',
    'rank.gumus':   'Gümüş',
    'rank.altin':   'Altın',
    'rank.platin':  'Platin',
    'rank.elmas':   'Elmas',
    'rank.usta':    'Usta',
  },

  en: {
    /* nav */
    'nav.home':      'Home',
    'nav.play':      'Play',
    'nav.spectate':  'Watch',
    'nav.vscomp':    'vs. Computer',
    'nav.profile':   'Profile',
    'nav.login':     'Log In',
    'nav.register':  'Sign Up',
    'nav.logout':    'Log Out',

    /* lobby */
    'lobby.title':      '⬡ ROTAKA ⬡',
    'lobby.subtitle':   'Online Multiplayer',
    'lobby.create':     'Create Room  (Play as White)',
    'lobby.join':       'Join Room',
    'lobby.join_ph':    'Enter room code…',
    'lobby.join_btn':   'Join',
    'lobby.or':         '— or —',
    'lobby.waiting':    'Waiting for opponent…',
    'lobby.room_code':  'Your Room Code:',
    'lobby.room_hint':  'Send this code to your friend',
    'lobby.live':       'Live Games',
    'lobby.no_live':    'No live games right now.',
    'lobby.watch':      'Watch',
    'lobby.moves':      'moves',

    /* game */
    'game.your_turn':   'Your Turn',
    'game.opp_turn':    'Opponent Thinking…',
    'game.boost':       '⚡ BOOST',
    'game.you':         'YOU',
    'game.white':       'WHITE',
    'game.black':       'BLACK',
    'game.move':        'Move',
    'game.inf_top':     "Black's Home",
    'game.inf_bot':     "White's Home",
    'game.repeat':      'Repeat',
    'game.inactive':    'Inactive',
    'game.notation':    'Move Notation',
    'game.chat':        'Chat',
    'game.chat_ph':     'Type a message…',
    'game.send':        'Send',
    'game.swap_title':  '👑 PIE RULE',
    'game.swap_desc':   "You've seen White's first move. Do you want to swap roles?",
    'game.swap_keep':   'Stay as Black',
    'game.swap_do':     '⇄ SWAP ROLES',
    'game.swap_wait':   '⏳ Opponent is deciding on the Pie Rule…',
    'game.over':        'Game Over!',
    'game.lobby':       'Back to Lobby',
    'game.elo_change':  'ELO Change',
    'game.opp_left':    'Opponent Left',
    'game.opp_left_msg':'Your opponent has disconnected.',

    /* profile */
    'profile.stats':    'Statistics',
    'profile.games':    'Total Games',
    'profile.wins':     'Wins',
    'profile.losses':   'Losses',
    'profile.draws':    'Draws',
    'profile.winpct':   'Win %',
    'profile.inf_wins': 'Wins by Infiltration',
    'profile.elim_wins':'Wins by Elimination',
    'profile.history':  'Recent Games',
    'profile.friends':  'Friends',
    'profile.add_friend':'Add Friend',
    'profile.friend_sent':'Request Sent',
    'profile.accept':   'Accept',
    'profile.rank':     'Rank',
    'profile.elo':      'ELO',
    'profile.no_games': 'No games yet.',
    'profile.no_friends':'No friends yet.',

    /* auth */
    'login.title':      'Log In',
    'login.username':   'Username',
    'login.password':   'Password',
    'login.submit':     'Log In',
    'login.no_acc':     "Don't have an account?",
    'login.register':   'Sign Up',
    'login.google':     'Sign In with Google',
    'register.title':   'Sign Up',
    'register.submit':  'Create Account',
    'register.have_acc':'Already have an account?',

    /* vs computer */
    'vscomp.title':     'Play vs Computer',
    'vscomp.coming':    'Coming Soon…',
    'vscomp.desc':      'Our trained Rotaka AI will be embedded here. Online play is available now.',

    /* spectate */
    'spectate.title':   'Live Games',
    'spectate.none':    'No live games at the moment.',
    'spectate.watch':   'Watch',
    'spectate.moves':   'moves',

    /* ranks */
    'rank.bronz':   'Bronze',
    'rank.gumus':   'Silver',
    'rank.altin':   'Gold',
    'rank.platin':  'Platinum',
    'rank.elmas':   'Diamond',
    'rank.usta':    'Master',
  },
};

function getLang() {
  return localStorage.getItem('rotaka_lang') || document.documentElement.lang || 'tr';
}

function t(key) {
  const lang = getLang();
  return (TRANSLATIONS[lang] && TRANSLATIONS[lang][key])
      || (TRANSLATIONS['tr'] && TRANSLATIONS['tr'][key])
      || key;
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
}

function setLang(lang) {
  localStorage.setItem('rotaka_lang', lang);
  document.documentElement.lang = lang;
  applyTranslations();
  // persist to server if logged in
  fetch('/api/language', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lang }),
  });
}

document.addEventListener('DOMContentLoaded', applyTranslations);
