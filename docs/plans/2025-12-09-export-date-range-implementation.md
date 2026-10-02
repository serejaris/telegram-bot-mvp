# Export Date Range Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add date range export (week/month/custom) to the chat export tab.

**Architecture:** New API endpoint `/api/chats/{id}/messages/export` with `from`/`to` params. Frontend gets preset buttons (week/month) plus custom date pickers. Uses existing `get_chat_messages_by_date` pattern for DB query.

**Tech Stack:** aiohttp, PostgreSQL, Jinja2, vanilla JS

---

### Task 1: Add DB query function for date range

**Files:**
- Modify: `app/models.py:470-515` (after `get_chat_messages_by_date`)

**Step 1: Add the function**

Add after line 515 in `app/models.py`:

```python
async def get_chat_messages_by_date_range(
    chat_id: int,
    date_from: str,  # format: YYYY-MM-DD
    date_to: str,    # format: YYYY-MM-DD
) -> List[Dict[str, Any]]:
    """Получает все сообщения чата за диапазон дат (включительно, UTC+3)."""
    async with get_cursor() as cur:
        await cur.execute("""
            SELECT
                m.message_id,
                m.message_type,
                m.text,
                m.caption,
                m.sent_at,
                m.edited_at,
                m.reply_to_message_id,
                u.id as user_id,
                u.first_name,
                u.last_name,
                u.username
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.chat_id = %s
              AND (m.sent_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date >= %s::date
              AND (m.sent_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date <= %s::date
            ORDER BY m.sent_at ASC
        """, (chat_id, date_from, date_to))

        rows = await cur.fetchall()
        return [
            {
                "message_id": row[0],
                "message_type": row[1],
                "text": row[2],
                "caption": row[3],
                "sent_at": row[4],
                "edited_at": row[5],
                "reply_to_message_id": row[6],
                "user": {
                    "id": row[7],
                    "first_name": row[8],
                    "last_name": row[9],
                    "username": row[10],
                } if row[7] else None
            }
            for row in rows
        ]
```

**Step 2: Commit**

```bash
git add app/models.py
git commit -m "feat: add get_chat_messages_by_date_range query"
```

---

### Task 2: Add API endpoint for export

**Files:**
- Modify: `app/web/routes.py:17-25` (imports)
- Modify: `app/web/routes.py:219` (after `api_chat_messages_daily`)
- Modify: `app/web/routes.py:438` (route registration)

**Step 1: Update imports**

In `app/web/routes.py`, change line 21 from:
```python
    get_chat_messages_by_date,
```
to:
```python
    get_chat_messages_by_date,
    get_chat_messages_by_date_range,
```

**Step 2: Add endpoint function**

Add after `api_chat_messages_daily` function (after line 219):

```python
@require_auth
async def api_chat_messages_export(request: web.Request) -> web.Response:
    """API: экспорт сообщений чата за диапазон дат (UTC+3)."""
    try:
        chat_id = int(request.match_info["chat_id"])
        date_from = request.query.get("from")
        date_to = request.query.get("to")

        if not date_from or not date_to:
            return json_response(
                {"error": "from and to parameters required (YYYY-MM-DD)"},
                status=400
            )

        # Validate date format
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            return json_response(
                {"error": "invalid date format, use YYYY-MM-DD"},
                status=400
            )

        # Validate range
        if date_from > date_to:
            return json_response(
                {"error": "from date must be before or equal to to date"},
                status=400
            )

        # Get chat info
        chat = await get_chat_by_id(chat_id)
        if not chat:
            return json_response({"error": "chat not found"}, status=404)

        messages = await get_chat_messages_by_date_range(chat_id, date_from, date_to)

        # Serialize datetime
        for msg in messages:
            if msg["sent_at"]:
                msg["sent_at"] = msg["sent_at"].isoformat()
            if msg["edited_at"]:
                msg["edited_at"] = msg["edited_at"].isoformat()

        return json_response({
            "chat_id": chat_id,
            "chat_title": chat.get("title"),
            "period": {
                "from": date_from,
                "to": date_to,
            },
            "timezone": "UTC+3",
            "messages_count": len(messages),
            "messages": messages,
        })
    except ValueError:
        return json_response({"error": "invalid chat_id"}, status=400)
    except Exception as e:
        logger.error(f"API export messages error: {e}")
        return json_response({"error": str(e)}, status=500)
```

**Step 3: Register route**

Add after line 434 (`/messages/daily` route):

```python
    app.router.add_get("/api/chats/{chat_id}/messages/export", api_chat_messages_export)
```

**Step 4: Commit**

```bash
git add app/web/routes.py
git commit -m "feat: add /api/chats/{id}/messages/export endpoint"
```

---

### Task 3: Update Export tab UI

**Files:**
- Modify: `app/web/templates/messages.html:409-444` (CSS)
- Modify: `app/web/templates/messages.html:733-749` (HTML)

**Step 1: Update CSS**

Replace the `/* ─── Export Tab ─── */` section (lines 409-444) with:

```css
    /* ─── Export Tab ─── */
    .export-container {
        display: grid;
        gap: 20px;
        max-width: 500px;
    }

    .export-period-selector {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .export-period-selector label {
        color: var(--dim);
        font-size: 0.85em;
        margin-right: 8px;
    }

    .export-period-btn {
        padding: 8px 16px;
        border: 1px solid var(--border);
        background: transparent;
        color: var(--dim);
        font-family: var(--font);
        font-size: 0.85em;
        cursor: pointer;
        transition: all 0.15s;
    }

    .export-period-btn:hover {
        border-color: var(--fg);
        color: var(--fg);
    }

    .export-period-btn.selected {
        border-color: var(--fg);
        color: var(--fg);
        background: var(--hover);
    }

    .export-date-range {
        display: none;
        gap: 12px;
        align-items: center;
        padding: 16px;
        border: 1px dashed var(--border);
    }

    .export-date-range.visible {
        display: flex;
    }

    .export-date-range label {
        color: var(--dim);
        font-size: 0.85em;
    }

    .date-input {
        padding: 8px 12px;
        border: 1px solid var(--border);
        background: var(--bg);
        color: var(--fg);
        font-family: var(--font);
        font-size: 0.9em;
    }

    .date-input:focus {
        outline: none;
        border-color: var(--fg);
    }

    .export-hint {
        color: var(--muted);
        font-size: 0.8em;
    }
```

**Step 2: Update HTML**

Replace the Export tab content (lines 733-749) with:

```html
<!-- Export Tab -->
<div id="tab-export" class="tab-content">
    <div class="export-container">
        <div class="export-period-selector">
            <label>период:</label>
            <button class="export-period-btn selected" data-period="week">[ неделя ]</button>
            <button class="export-period-btn" data-period="month">[ месяц ]</button>
            <button class="export-period-btn" data-period="custom">[ диапазон ]</button>
        </div>

        <div id="export-date-range" class="export-date-range">
            <label>от:</label>
            <input type="date" id="export-date-from" class="date-input">
            <label>до:</label>
            <input type="date" id="export-date-to" class="date-input">
        </div>

        <button id="export-btn" class="generate-btn" onclick="downloadExport()">
            скачать JSON
        </button>

        <div class="export-hint">
            экспорт за полный период (00:00–23:59 каждого дня) · UTC+3 (Москва)
        </div>
    </div>
</div>
```

**Step 3: Commit**

```bash
git add app/web/templates/messages.html
git commit -m "feat: update export tab UI with period presets"
```

---

### Task 4: Update Export tab JavaScript

**Files:**
- Modify: `app/web/templates/messages.html:923-972` (JS export section)

**Step 1: Replace export JS**

Replace the export JavaScript section (from `// Export: set default date` to end of `downloadByDate` function, approximately lines 923-972) with:

```javascript
    // Export functionality
    let selectedExportPeriod = 'week';

    // Period button selection
    document.querySelectorAll('.export-period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.export-period-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedExportPeriod = btn.dataset.period;

            const dateRange = document.getElementById('export-date-range');
            if (selectedExportPeriod === 'custom') {
                dateRange.classList.add('visible');
            } else {
                dateRange.classList.remove('visible');
            }
        });
    });

    // Initialize date inputs with defaults
    (function initExportDates() {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        const weekAgo = new Date(yesterday);
        weekAgo.setDate(weekAgo.getDate() - 6);

        document.getElementById('export-date-from').value = weekAgo.toISOString().split('T')[0];
        document.getElementById('export-date-to').value = yesterday.toISOString().split('T')[0];
    })();

    // Calculate date range based on selected period
    function getExportDateRange() {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (selectedExportPeriod === 'week') {
            const from = new Date(yesterday);
            from.setDate(from.getDate() - 6);
            return {
                from: from.toISOString().split('T')[0],
                to: yesterday.toISOString().split('T')[0]
            };
        } else if (selectedExportPeriod === 'month') {
            const from = new Date(yesterday);
            from.setDate(from.getDate() - 29);
            return {
                from: from.toISOString().split('T')[0],
                to: yesterday.toISOString().split('T')[0]
            };
        } else {
            // custom
            return {
                from: document.getElementById('export-date-from').value,
                to: document.getElementById('export-date-to').value
            };
        }
    }

    // Download export
    async function downloadExport() {
        const btn = document.getElementById('export-btn');
        const range = getExportDateRange();

        if (!range.from || !range.to) {
            alert('выберите даты');
            return;
        }

        if (range.from > range.to) {
            alert('дата "от" должна быть раньше даты "до"');
            return;
        }

        const originalText = btn.textContent;
        btn.textContent = '...';
        btn.disabled = true;

        try {
            const response = await fetch(
                `/api/chats/${CHAT_ID}/messages/export?from=${range.from}&to=${range.to}`
            );
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `chat_${CHAT_ID}_${range.from}_${range.to}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            btn.textContent = 'ok';
            setTimeout(() => btn.textContent = originalText, 1000);
        } catch (e) {
            btn.textContent = 'ошибка';
            setTimeout(() => btn.textContent = originalText, 2000);
            console.error('Export error:', e);
        } finally {
            btn.disabled = false;
        }
    }
```

**Step 2: Remove old downloadByDate function**

Delete the old `initExportDate` and `downloadByDate` functions if they still exist.

**Step 3: Commit**

```bash
git add app/web/templates/messages.html
git commit -m "feat: add export JS for period presets and date range"
```

---

### Task 5: Test locally

**Step 1: Run the server**

```bash
source .venv/bin/activate && python main.py
```

**Step 2: Test API endpoint**

```bash
curl "http://localhost:8080/api/chats/{CHAT_ID}/messages/export?from=2025-12-01&to=2025-12-09" \
  -u admin:password
```

Expected: JSON with messages array, chat_title, period object, messages_count.

**Step 3: Test error cases**

```bash
# Missing params
curl "http://localhost:8080/api/chats/{CHAT_ID}/messages/export" -u admin:password
# Expected: 400 with "from and to parameters required"

# Invalid date order
curl "http://localhost:8080/api/chats/{CHAT_ID}/messages/export?from=2025-12-09&to=2025-12-01" -u admin:password
# Expected: 400 with "from date must be before"
```

**Step 4: Test UI**

1. Open chat page → Export tab
2. Click "неделя" → click "скачать JSON" → file downloads
3. Click "месяц" → click "скачать JSON" → file downloads
4. Click "диапазон" → date pickers appear → set dates → download

**Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: export date range tweaks"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | DB query function | `app/models.py` |
| 2 | API endpoint | `app/web/routes.py` |
| 3 | Export tab UI | `app/web/templates/messages.html` (CSS + HTML) |
| 4 | Export tab JS | `app/web/templates/messages.html` (JS) |
| 5 | Test locally | Manual testing |
