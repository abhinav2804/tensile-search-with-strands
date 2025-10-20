
# 📊 Generative Indexing Dashboard UI

An interactive dashboard for monitoring and visualizing the Generative Indexing pipeline in real time.

## Features

- 🚦 **Live Progress Updates:** See indexing status and pipeline steps as they happen
- 📈 **Visual Analytics:** View charts and metrics for processed documents
- 🖥️ **Responsive Design:** Works on desktop and mobile
- 🔗 **API Integration:** Connects to backend FastAPI endpoints for live data

## File Structure

```
ui/
├── ui.py                # Dashboard UI server (Flask or FastAPI)
├── static/
│   ├── live-dashboard.html  # Main dashboard HTML
│   ├── style.css            # Custom styles
│   └── script.js            # Dashboard interactivity
```

## Quick Start

1. **Install dependencies** (if any):
    ```bash
    pip install flask fastapi
    ```

2. **Run the dashboard server:**
    ```bash
    python ui.py
    ```

3. **Open your browser:**
    Navigate to [http://localhost:5000](http://localhost:5000) or the port shown in your terminal.

## Customization

- Edit `static/style.css` for custom styles
- Update `static/script.js` for new charts or UI features
- Modify `live-dashboard.html` for layout changes

## Integration

The dashboard fetches live data from the backend API (see main project README for API details). SSE or WebSocket can be used for real-time updates.

## Example Screenshot

![Dashboard Example](https://raw.githubusercontent.com/abhinav2804/tensile-search-with-strands/main/generativeIndexing/ui/static/dashboard-screenshot.png)

---
Made with ❤️ for Generative Indexing
