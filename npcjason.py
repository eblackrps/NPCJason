from npcjason_app.app import NPCJasonApp, parse_args
from npcjason_app.version import APP_NAME, APP_VERSION
import sys


if __name__ == "__main__":
    print("=" * 40)
    print(f"  {APP_NAME} Desktop Pet v{APP_VERSION}")
    print("  Left-click  = Dance + Say Something")
    print("  Right-click = Menu")
    print("  Drag to move around!")
    print("=" * 40)
    app = NPCJasonApp(parse_args(sys.argv[1:]))
    app.run()
