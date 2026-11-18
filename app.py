import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session, jsonify, Response

app = Flask(__name__)
app.secret_key = 'learning_support_colab_secret_key'
app.config['TEMPLATES_AUTO_RELOAD'] = True

USERS = {
    "chiencity": {"password": "admin123", "role": "admin"},
    "student1": {"password": "password123", "role": "student"}
}

HOMEWORKS = [
    {
        "id": "1",
        "title": "📌 数学レポート提出期限",
        "start": "2026-10-25",
        "backgroundColor": "#3b82f6",
        "borderColor": "#2563eb",
        "url": "https://docs.google.com/forms/",
        "type": "hw"
    },
    {
        "id": "2",
        "title": "📌 【再提出】物理小テスト",
        "start": "2026-10-28",
        "backgroundColor": "#3b82f6",
        "borderColor": "#2563eb",
        "url": "#",
        "type": "hw"
    }
]

PERSONAL_MEMOS = []

LATEST_NOTIFICATION = {"title": "", "body": "", "timestamp": 0}

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "name": "学習支援ポータル",
        "short_name": "学習ポータル",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#2563eb",
        "icons": [
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%232563eb'/><text x='50' y='68' font-size='55' text-anchor='middle'>📚</text></svg>",
                "sizes": "192x192",
                "type": "image/svg+xml"
            },
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%232563eb'/><text x='50' y='68' font-size='55' text-anchor='middle'>📚</text></svg>",
                "sizes": "512x512",
                "type": "image/svg+xml"
            }
        ]
    }
    return jsonify(manifest_data)

@app.route('/sw.js')
def service_worker():
    sw_code = """
    self.addEventListener('install', (event) => {
        self.skipWaiting();
    });
    self.addEventListener('activate', (event) => {
        event.waitUntil(clients.claim());
    });
    self.addEventListener('push', (event) => {
        const data = event.data ? event.data.json() : { title: '学習支援ポータル', body: '新しいお知らせがあります！' };
        event.waitUntil(
            self.registration.showNotification(data.title, {
                body: data.body,
                icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%232563eb'/><text x='50' y='68' font-size='55' text-anchor='middle'>📚</text></svg>"
            })
        );
    });
    self.addEventListener('notificationclick', (event) => {
        event.notification.close();
        event.waitUntil(clients.openWindow('/'));
    });
    """
    return Response(sw_code, mimetype='application/javascript')

@app.route('/api/check-notification')
def check_notification():
    since = float(request.args.get('since', 0))
    if LATEST_NOTIFICATION['timestamp'] > since:
        return jsonify({"has_new": True, "notification": LATEST_NOTIFICATION})
    return jsonify({"has_new": False})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>学習支援ポータル</title>
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#2563eb">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="学習ポータル">

  <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #334155; margin: 0; padding: 20px; }
    .header-bar { display: flex; justify-content: space-between; align-items: center; background: white; padding: 16px 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
    .user-info { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 1.05rem; }
    .header-actions { display: flex; align-items: center; gap: 10px; }
    .notify-btn { background: #f59e0b; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
    .notify-btn:hover { background: #d97706; }
    .logout-btn { color: #ef4444; text-decoration: none; font-weight: 600; padding: 6px 12px; border: 1px solid #fee2e2; border-radius: 6px; transition: 0.2s; font-size: 0.85rem; }
    .logout-btn:hover { background: #fef2f2; }
    
    .main-layout { display: flex; gap: 20px; flex-wrap: wrap; }
    .calendar-card { flex: 7; min-width: 320px; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.04); }
    .sidebar { flex: 3; min-width: 280px; display: flex; flex-direction: column; gap: 20px; }
    
    .card { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.04); }
    .card h3 { margin: 0 0 12px 0; font-size: 1.1rem; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; }
    
    .fc { --fc-border-color: #f1f5f9; --fc-button-bg-color: #2563eb; --fc-button-border-color: #2563eb; --fc-button-active-bg-color: #1d4ed8; }
    .fc .fc-toolbar-title { font-size: 1.25rem; font-weight: 700; color: #1e293b; }
    .fc .fc-button { border-radius: 8px; font-weight: 600; text-transform: capitalize; }
    .fc-theme-standard td, .fc-theme-standard th { border-color: #f1f5f9; }
    .fc-event { cursor: pointer; border-radius: 4px; padding: 2px 5px; font-size: 0.85rem; border: none; }

    .memo-input-group { display: flex; flex-direction: column; gap: 8px; }
    .memo-input-group input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.9rem; }
    .memo-btn { background: #10b981; color: white; border: none; padding: 8px; border-radius: 6px; cursor: pointer; font-weight: 600; }
    .memo-btn:hover { background: #059669; }

    .floating-btn { position: fixed; bottom: 24px; right: 24px; padding: 14px 24px; background: #2563eb; color: white; border: none; border-radius: 50px; cursor: pointer; font-weight: bold; font-size: 0.95rem; box-shadow: 0 8px 20px rgba(37,99,235,0.3); transition: 0.2s; z-index: 900; }
    .floating-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(37,99,235,0.4); }
    .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 1000; justify-content: center; align-items: center; }
    .modal-content { background: #0f172a; color: white; padding: 28px; border-radius: 16px; border: 1px solid #38bdf8; text-align: center; position: relative; max-width: 320px; width: 90%; }
    .roulette-container { position: relative; width: 220px; height: 220px; margin: 15px auto; }
    .pointer { position: absolute; top: -10px; left: 50%; transform: translateX(-50%); border-left: 10px solid transparent; border-right: 10px solid transparent; border-top: 20px solid #ef4444; z-index: 10; }
    .wheel { width: 100%; height: 100%; border-radius: 50%; border: 2px solid #38bdf8; transition: transform 4s cubic-bezier(0.15,0.9,0.2,1); }
    .center-cap { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); width: 28px; height: 28px; background: #1e293b; border: 2px solid #38bdf8; border-radius: 50%; }
  </style>
  <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(err => console.log('SW failed:', err));
      });
    }

    async function enableAndTestNotification() {
      if (!('Notification' in window)) {
        alert('このブラウザは通知機能に対応していません。');
        return;
      }
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        const reg = await navigator.serviceWorker.ready;
        reg.showNotification('📚 学習支援ポータル', {
          body: '通知の設定が完了しました！新しい課題の追加や期限をお知らせします。',
          icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%232563eb'/><text x='50' y='68' font-size='55' text-anchor='middle'>📚</text></svg>"
        });
      } else {
        alert('通知がブロックされています。ブラウザの設定から通知を許可してください。');
      }
    }

    // サーバーからの新着通知を定期チェック（ポーリング）
    let lastCheckedTime = Date.now() / 1000;
    setInterval(async () => {
      try {
        const res = await fetch('/api/check-notification?since=' + lastCheckedTime);
        const data = await res.json();
        if (data.has_new) {
          lastCheckedTime = data.notification.timestamp;
          if (Notification.permission === 'granted') {
            const reg = await navigator.serviceWorker.ready;
            reg.showNotification(data.notification.title, {
              body: data.notification.body,
              icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%232563eb'/><text x='50' y='68' font-size='55' text-anchor='middle'>📚</text></svg>"
            });
          }
        }
      } catch(e) {}
    }, 5000); // 5秒ごとにチェック

    var isAdmin = {{ is_admin | tojson }};
    var rawEvents = {{ events | tojson }};

    document.addEventListener('DOMContentLoaded', function() {
      var cal = new FullCalendar.Calendar(document.getElementById('calendar'), {
        initialView: 'dayGridMonth',
        locale: 'ja',
        headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek' },
        events: rawEvents,
        eventClick: function(info) {
          info.jsEvent.preventDefault(); 
          var selectedId = info.event.id;
          var selectedType = info.event.extendedProps.type;

          if (selectedType === 'memo') {
            if (confirm("自分のメモ『" + info.event.title + "』を削除しますか？")) {
              window.location.href = "/delete-memo?id=" + selectedId;
            }
          } else if (isAdmin) {
            if (confirm("【管理者】全体課題『" + info.event.title + "』を削除しますか？")) {
              window.location.href = "/delete-event?id=" + selectedId;
            }
          } else if (info.event.url && info.event.url !== "#") {
            window.open(info.event.url, '_blank');
          }
        }
      });
      cal.render();
      renderList();
    });

    function renderList() {
      var today = new Date().toISOString().split('T')[0];
      var evs = rawEvents.filter(e => e.start >= today).sort((a,b) => a.start.localeCompare(b.start));
      
      document.getElementById('list').innerHTML = evs.map(e => {
        var clickAttr = (e.url && e.url !== "#") ? `onclick="window.open('${e.url}','_blank')"` : '';
        var cursorStyle = (e.url && e.url !== "#") ? 'cursor:pointer;' : 'cursor:default;';
        var isMemo = e.type === 'memo';
        var badge = isMemo ? '<span style="color:#059669;font-size:0.75rem;font-weight:bold;">個人メモ</span>' : '<span style="color:#2563eb;font-size:0.75rem;font-weight:bold;">全体課題</span>';
        
        return `<div ${clickAttr} style="border-left:4px solid ${e.backgroundColor};background:#f8fafc;padding:10px;margin-bottom:8px;border-radius:6px;${cursorStyle}">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <small style="color:#64748b;">⏳ ${e.start.slice(5)}</small>${badge}
          </div>
          <div style="font-weight:600;margin-top:2px;">${e.title}</div>
        </div>`;
      }).join('') || '<p style="color:#94a3b8;font-size:0.9rem;">直近の予定はありません</p>';
    }

    const items = [{l:"30分",w:1},{l:"45分",w:30},{l:"1時間",w:160},{l:"1.5時間",w:320},{l:"2時間",w:150},{l:"3時間",w:38.7},{l:"6.5時間",w:0.3}];
    let rot = 0, isSecret = false;

    document.addEventListener('keydown', e => {
      if (e.ctrlKey && e.shiftKey && e.code === 'KeyH') {
        e.preventDefault(); isSecret = true;
        const cap = document.querySelector('.center-cap');
        if(cap) { cap.style.borderColor = '#facc15'; setTimeout(() => cap.style.borderColor = '#38bdf8', 600); }
      }
    });

    function openRoulette() { document.getElementById('modal').style.display = 'flex'; createWheel(); }
    function closeRoulette() { document.getElementById('modal').style.display = 'none'; }
    
    function createWheel() {
      const wheel = document.getElementById('wheel');
      if (wheel.children.length) return;
      let svg = ''; const step = 360 / items.length;
      items.forEach((item, i) => {
        const a1 = i * step, a2 = (i + 1) * step;
        const x1 = 50 + 50 * Math.cos(Math.PI * (a1 - 90) / 180), y1 = 50 + 50 * Math.sin(Math.PI * (a1 - 90) / 180);
        const x2 = 50 + 50 * Math.cos(Math.PI * (a2 - 90) / 180), y2 = 50 + 50 * Math.sin(Math.PI * (a2 - 90) / 180);
        const ta = a1 + step / 2, tx = 50 + 33 * Math.cos(Math.PI * (ta - 90) / 180), ty = 50 + 33 * Math.sin(Math.PI * (ta - 90) / 180);
        svg += `<path d="M 50 50 L ${x1} ${y1} A 50 50 0 0 1 ${x2} ${y2} Z" fill="hsl(${i * 50},70%,50%)"/>
                <text x="${tx}" y="${ty}" fill="white" font-size="5" text-anchor="middle" transform="rotate(${ta+90},${tx},${ty})">${item.l}</text>`;
      });
      wheel.innerHTML = `<svg viewBox="0 0 100 100" style="width:100%;height:100%">${svg}</svg>`;
    }

    function spin() {
      let idx = 6;
      if (!isSecret) {
        let total = items.reduce((s, i) => s + i.w, 0), rnd = Math.random() * total;
        for (let i = 0; i < items.length; i++) { if (rnd < items[i].w) { idx = i; break; } rnd -= items[i].w; }
      }
      isSecret = false;
      const step = 360 / items.length;
      rot += (360 * 5) + (360 - (idx * step + step / 2));
      document.getElementById('wheel').style.transform = `rotate(${rot}deg)`;
      setTimeout(() => {
        document.getElementById('res').innerText = "結果: " + items[idx].l;
      }, 4000);
    }
  </script>
</head>
<body>
  <div class="header-bar">
    <div class="user-info">
      <span>👤 ID: {{ user_id }}</span>
      {% if is_admin %}
        <span style="background:#dbeafe;color:#1e40af;padding:3px 8px;border-radius:12px;font-size:0.8rem;font-weight:600;">管理者</span>
      {% else %}
        <span style="background:#d1fae5;color:#065f46;padding:3px 8px;border-radius:12px;font-size:0.8rem;font-weight:600;">生徒</span>
      {% endif %}
    </div>
    <div class="header-actions">
      <button onclick="enableAndTestNotification()" class="notify-btn">🔔 通知をON・テスト</button>
      <a href="/logout" class="logout-btn">ログアウト</a>
    </div>
  </div>

  {% if is_admin %}
  <div style="background: white; padding: 16px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); border-left: 5px solid #2563eb;">
    <h4 style="margin: 0 0 10px 0; color: #1e293b;">📢 全体課題の追加（管理者権限）</h4>
    <form action="/add-event" method="POST" style="display: flex; gap: 10px; flex-wrap: wrap;">
      <input name="title" placeholder="全体課題名" required style="flex: 2; min-width: 150px; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px;">
      <input type="date" name="date" required style="flex: 1; min-width: 130px; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px;">
      <input name="url" placeholder="提出先URL (任意)" style="flex: 2; min-width: 150px; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px;">
      <button type="submit" style="background: #2563eb; color: white; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-weight: 600;">追加</button>
    </form>
  </div>
  {% endif %}

  <div class="main-layout">
    <div class="calendar-card">
      <div id="calendar"></div>
    </div>

    <div class="sidebar">
      <div class="card" style="border-top: 4px solid #10b981;">
        <h3>📝 自分用メモを追加</h3>
        <form action="/add-memo" method="POST" class="memo-input-group">
          <input name="title" placeholder="メモの内容 (例: 単語帳P20まで)" required>
          <input type="date" name="date" required>
          <button type="submit" class="memo-btn">カレンダーに保存</button>
        </form>
        <p style="font-size: 0.75rem; color: #94a3b8; margin: 8px 0 0 0;">※ このメモは自分だけに表示されます</p>
      </div>

      <div class="card">
        <h3>🏁 予定・課題一覧</h3>
        <div id="list"></div>
      </div>
    </div>
  </div>

  <button class="floating-btn" onclick="openRoulette()">🎯 勉強時間ルーレット</button>

  <div id="modal" class="modal-overlay" onclick="if(event.target===this)closeRoulette()">
    <div class="modal-content">
      <button onclick="closeRoulette()" style="position:absolute;top:10px;right:10px;background:none;border:none;color:white;cursor:pointer;font-size:1.2rem;">✕</button>
      <h3 style="margin-top:0;">🎯 勉強時間決定ルーレット</h3>
      <div class="roulette-container"><div class="pointer"></div><div class="wheel" id="wheel"></div><div class="center-cap"></div></div>
      <button onclick="spin()" style="padding:10px 24px;background:#2563eb;color:white;border:none;border-radius:6px;cursor:pointer;font-weight:600;width:100%;">回す</button>
      <div id="res" style="margin-top:12px;font-weight:bold;font-size:1.1rem;color:#38bdf8;"></div>
    </div>
  </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>ログイン | 学習支援</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#2563eb">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f1f5f9; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
    .container { display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; max-width: 680px; width: 100%; }
    .card { background: white; padding: 32px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); flex: 1; min-width: 280px; }
    h2 { margin-top: 0; font-size: 1.25rem; color: #1e293b; display: flex; align-items: center; gap: 8px; }
    input { width: 100%; padding: 12px; margin: 8px 0 16px; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 0.95rem; }
    input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }
    button { width: 100%; padding: 12px; border: none; border-radius: 8px; font-weight: 600; font-size: 0.95rem; cursor: pointer; transition: background 0.2s; }
    .btn-blue { background: #2563eb; color: white; } .btn-blue:hover { background: #1d4ed8; }
    .btn-green { background: #10b981; color: white; } .btn-green:hover { background: #059669; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h2>👤 ログイン</h2>
      <form action="/login" method="POST">
        <input name="userid" placeholder="学籍番号 / ID" required>
        <input type="password" name="password" placeholder="パスワード" required>
        <button class="btn-blue">ログイン</button>
      </form>
    </div>
    <div class="card" style="border-top: 4px solid #10b981;">
      <h2 style="color:#059669;">📝 新規登録</h2>
      <form action="/register" method="POST">
        <input name="userid" placeholder="学籍番号 / ID" required>
        <input type="password" name="password" placeholder="パスワード" required>
        <button class="btn-green">登録する</button>
      </form>
    </div>
  </div>
</body>
</html>
"""

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template_string(LOGIN_TEMPLATE)
    
    user_id = session['user_id']
    role = session.get('role', 'student')
    is_admin = (role == 'admin')

    events = list(HOMEWORKS)
    for memo in PERSONAL_MEMOS:
        if memo['userId'] == user_id:
            events.append(memo)

    return render_template_string(HTML_TEMPLATE, user_id=user_id, is_admin=is_admin, events=events)

@app.route('/login', methods=['POST'])
def login():
    userid = request.form.get('userid')
    password = request.form.get('password')

    if userid in USERS and USERS[userid]['password'] == password:
        session['user_id'] = userid
        session['role'] = USERS[userid]['role']
    return redirect('/')

@app.route('/register', methods=['POST'])
def register():
    userid = request.form.get('userid')
    password = request.form.get('password')

    if userid and password and userid not in USERS:
        USERS[userid] = {"password": password, "role": "student"}
        session['user_id'] = userid
        session['role'] = "student"
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add-event', methods=['POST'])
def add_event():
    if session.get('role') == 'admin':
        title = request.form.get('title', '課題')
        date = request.form.get('date', '2026-10-25')
        url = request.form.get('url', '')

        HOMEWORKS.append({
            "id": str(int(datetime.now().timestamp() * 1000)),
            "title": f"📌 {title}",
            "start": date,
            "backgroundColor": "#3b82f6",
            "borderColor": "#2563eb",
            "url": url if url else "#",
            "type": "hw"
        })

        global LATEST_NOTIFICATION
        LATEST_NOTIFICATION = {
            "title": "📢 新しい全体課題",
            "body": f"「{title}」(期限: {date}) が追加されました！",
            "timestamp": datetime.now().timestamp()
        }

    return redirect('/')

@app.route('/add-memo', methods=['POST'])
def add_memo():
    if 'user_id' in session:
        title = request.form.get('title', '用事')
        date = request.form.get('date', '2026-10-25')

        PERSONAL_MEMOS.append({
            "id": str(int(datetime.now().timestamp() * 1000)),
            "userId": session['user_id'],
            "title": f"📝 {title}",
            "start": date,
            "backgroundColor": "#10b981",
            "borderColor": "#059669",
            "url": "#",
            "type": "memo"
        })
    return redirect('/')

@app.route('/delete-event')
def delete_event():
    if session.get('role') == 'admin':
        event_id = request.args.get('id')
        global HOMEWORKS
        HOMEWORKS = [hw for hw in HOMEWORKS if hw['id'] != event_id]
    return redirect('/')

@app.route('/delete-memo')
def delete_memo():
    if 'user_id' in session:
        memo_id = request.args.get('id')
        global PERSONAL_MEMOS
        PERSONAL_MEMOS = [m for m in PERSONAL_MEMOS if not (m['id'] == memo_id and m['userId'] == session['user_id'])]
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
