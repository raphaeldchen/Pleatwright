"""python -m pleatwright_app [--port 8000] [--no-ui]  ->  http://127.0.0.1:<port>"""
import argparse
import os


def main(argv=None) -> None:
    import uvicorn

    from .api import VITE_PORT, create_app
    ap = argparse.ArgumentParser(prog="python -m pleatwright_app")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-ui", action="store_true", help="API only (use with `npm run dev`)")
    a = ap.parse_args(argv)
    dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist"))
    app = create_app(static_dir=None if a.no_ui else dist,
                     allowed_origin_ports={a.port, VITE_PORT})
    uvicorn.run(app, host="127.0.0.1", port=a.port)


if __name__ == "__main__":
    main()
