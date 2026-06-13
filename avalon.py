import flet as ft
import os

MISSION_SIZES = {
    5: [2, 3, 2, 3, 3],
    6: [2, 3, 4, 3, 4],
    7: [2, 3, 3, 4, 4],
    8: [3, 4, 4, 5, 5],
    9: [3, 4, 4, 5, 5],
    10: [3, 4, 4, 5, 5],
}

class GameState:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.is_setup_complete = False
        self.total_players = 5
        self.players = []
        self.history = []
        self.redo_stack = []
        self.current_mission = 1
        self.current_team_attempt = 1
        self.current_leader_idx = 0
        self.selected_team = set()
        self.current_votes = {}

    def start_game(self, players_count):
        self.total_players = players_count
        self.players = [f"玩家 {i+1}" for i in range(players_count)]
        self.current_votes = {player: "❌" for player in self.players}
        self.history = []
        self.redo_stack = []
        self.current_mission = 1
        self.current_team_attempt = 1
        self.current_leader_idx = 0
        self.selected_team.clear()
        self.is_setup_complete = True

game = GameState()

def main(page: ft.Page):
    page.title = "阿瓦隆戰況推演系統"
    page.bgcolor = ft.Colors.BLACK
    
    def on_broadcast_message(message):
        build_current_view()
    
    page.pubsub.subscribe(on_broadcast_message)

    def build_current_view():
        page.views.clear()
        
        if page.route == "/board":
            if not game.is_setup_complete:
                page.views.append(ft.View(route="/board", controls=[ft.Text("等待遊戲開始...", color=ft.Colors.WHITE38)], bgcolor=ft.Colors.BLACK))
            else:
                page.views.append(ft.View(route="/board", controls=[ft.Text("阿瓦隆戰報", size=20, color=ft.Colors.WHITE), create_board_table()], bgcolor=ft.Colors.BLACK))
        else:
            if not game.is_setup_complete:
                page.views.append(ft.View(route="/admin", controls=[ft.Text("設定遊戲", color=ft.Colors.WHITE), create_setup_controls()], bgcolor=ft.Colors.BLACK))
            else:
                page.views.append(ft.View(route="/admin", controls=[ft.Text(f"任務 {game.current_mission}", color=ft.Colors.WHITE), create_admin_controls(), ft.ElevatedButton("送出", on_click=process_voting_result)], bgcolor=ft.Colors.BLACK))
        page.update()

    def create_setup_controls():
        drop = ft.Dropdown(value="5", options=[ft.dropdown.Option(str(i)) for i in range(5, 11)])
        return ft.Column([drop, ft.ElevatedButton("開始", on_click=lambda e: (game.start_game(int(drop.value)), page.pubsub.send_all("update")))])

    def create_admin_controls():
        controls = []
        for p in game.players:
            controls.append(ft.Row([
                ft.Text(p, color=ft.Colors.WHITE),
                ft.Checkbox(on_change=lambda e, p=p: (game.selected_team.add(p) if e.control.value else game.selected_team.discard(p))),
                ft.TextButton(game.current_votes[p], on_click=lambda e, p=p: (setattr(game, 'current_votes', {**game.current_votes, p: "⭕" if game.current_votes[p] == "❌" else "❌"}), build_current_view()))
            ]))
        return ft.Column(controls)

    def create_board_table():
        rows = []
        for h in game.history:
            cells = [ft.DataCell(ft.Text(h["round"], color=ft.Colors.WHITE)), ft.DataCell(ft.Text(h["leader"], color=ft.Colors.WHITE)), ft.DataCell(ft.Text(h["status"], color=ft.Colors.WHITE))]
            for p in game.players:
                vote = h["votes"].get(p, "-")
                cells.append(ft.DataCell(ft.Container(
                    content=ft.Icon(ft.Icons.LOCAL_POLICE, color=ft.Colors.RED) if p in h["team"] else ft.Container(), 
                    bgcolor=ft.Colors.WHITE if vote == "⭕" else ft.Colors.GREY_800, 
                    width=40, height=30, alignment=ft.alignment.center
                )))
            rows.append(ft.DataRow(cells=cells))
        return ft.DataTable(columns=[ft.DataColumn(ft.Text("局", color=ft.Colors.WHITE)), ft.DataColumn(ft.Text("隊長", color=ft.Colors.WHITE)), ft.DataColumn(ft.Text("結果", color=ft.Colors.WHITE))] + [ft.DataColumn(ft.Text(p, color=ft.Colors.WHITE)) for p in game.players], rows=rows)

    def process_voting_result(e):
        game.history.append({"round": f"{game.current_mission}-{game.current_team_attempt}", "leader": game.players[game.current_leader_idx], "team": list(game.selected_team), "votes": game.current_votes.copy(), "status": "成功"})
        game.current_mission += 1; game.current_votes = {p: "❌" for p in game.players}; game.selected_team.clear(); page.pubsub.send_all("update")

    page.on_route_change = lambda e: build_current_view()
    build_current_view()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0")
