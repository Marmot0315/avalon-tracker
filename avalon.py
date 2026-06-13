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
                page.views.append(ft.View(route="/board", controls=[ft.Text("等待書記端設定遊戲人數並開始遊戲...", color=ft.Colors.WHITE38, size=20)], bgcolor=ft.Colors.BLACK))
            else:
                page.views.append(ft.View(route="/board", controls=[ft.Text(f"阿瓦隆戰報看板 ({game.total_players}人局)", size=24, color=ft.Colors.WHITE70, weight=ft.FontWeight.BOLD), ft.Divider(color=ft.Colors.WHITE24), create_board_table()], bgcolor=ft.Colors.BLACK))
        else:
            if not game.is_setup_complete:
                page.views.append(ft.View(route="/admin", controls=[ft.Text("⚙️ 遊戲初始設定", size=24, color=ft.Colors.WHITE70, weight=ft.FontWeight.BOLD), ft.Divider(color=ft.Colors.WHITE24), ft.Text("請選擇本局玩家總數：", color=ft.Colors.WHITE54, size=16), create_setup_controls()], bgcolor=ft.Colors.BLACK))
            else:
                required_team_size = MISSION_SIZES[game.total_players][game.current_mission - 1]
                is_fifth_attempt = game.current_team_attempt == 5
                submit_btn_text = "🚨 強制執行並結算" if is_fifth_attempt else "結算送出"
                submit_btn_color = ft.Colors.RED_900 if is_fifth_attempt else ft.Colors.BLUE_GREY_900

                page.views.append(ft.View(
                    route="/admin",
                    appbar=ft.AppBar(title=ft.Text(f"任務 {game.current_mission} - 第 {game.current_team_attempt} 次派票", size=18, color=ft.Colors.WHITE70), bgcolor=ft.Colors.BLACK, actions=[ft.TextButton("重新開始", icon=ft.Icons.RESTART_ALT, icon_color=ft.Colors.RED_400, style=ft.ButtonStyle(color=ft.Colors.RED_400), on_click=confirm_reset_game)]),
                    controls=[
                        ft.Row([ft.Text(f"當前隊長：{game.players[game.current_leader_idx]}", size=14, color=ft.Colors.WHITE38), ft.Text(f"應派人數：{required_team_size} 人 (已選: {len(game.selected_team)})", size=14, color=ft.Colors.AMBER_400 if len(game.selected_team) != required_team_size else ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(color=ft.Colors.WHITE24),
                        create_admin_controls(),
                        ft.Divider(color=ft.Colors.WHITE10),
                        ft.Row([
                            ft.Row([ft.IconButton(icon=ft.Icons.UNDO, on_click=undo_last_action, disabled=len(game.history) == 0, icon_color=ft.Colors.WHITE70, bgcolor=ft.Colors.GREY_900), ft.IconButton(icon=ft.Icons.REDO, on_click=redo_action, disabled=len(game.redo_stack) == 0, icon_color=ft.Colors.WHITE70, bgcolor=ft.Colors.GREY_900)], spacing=10),
                            ft.ElevatedButton(submit_btn_text, on_click=process_voting_result, style=ft.ButtonStyle(bgcolor=submit_btn_color, color=ft.Colors.WHITE, padding=ft.Padding(left=30, top=15, right=30, bottom=15)), height=60)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], bgcolor=ft.Colors.BLACK
                ))
        page.update()

    # --- 關鍵修正：彈窗邏輯更新 ---
    def show_mission_result_dialog():
        dlg = ft.AlertDialog(
            title=ft.Text("🚀 任務出發！"),
            content=ft.Column([ft.Text("請結算失敗票數："), fail_dropdown := ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(len(game.selected_team) + 1)], value="0")], tight=True),
            actions=[ft.TextButton("確認結算", on_click=lambda e: (setattr(dlg, 'open', False), page.update(), finalize_round(calculate_status(int(fail_dropdown.value)))))],
            bgcolor=ft.Colors.GREY_900
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def confirm_reset_game(e):
        def do_reset(e):
            game.reset_game()
            reset_dlg.open = False
            page.update()
            page.pubsub.send_all("update")
        reset_dlg = ft.AlertDialog(title=ft.Text("⚠️ 重新開始"), content=ft.Text("確定重來？"), actions=[ft.TextButton("確定", on_click=do_reset)])
        page.dialog = reset_dlg
        reset_dlg.open = True
        page.update()

    def calculate_status(fail_count):
        if fail_count == 0: return "成功"
        if fail_count == 1 and game.total_players >= 7 and game.current_mission == 4: return "成功 (1敗)"
        return f"失敗 ({fail_count}敗)"

    def finalize_round(mission_status):
        round_tag = f"{game.current_mission}-{game.current_team_attempt}"
        game.history.append({"round": round_tag, "leader": game.players[game.current_leader_idx], "team": list(game.selected_team), "votes": game.current_votes.copy(), "status": mission_status})
        game.redo_stack.clear()
        if "成功" in mission_status or "失敗" in mission_status: game.current_mission += 1; game.current_team_attempt = 1
        else: game.current_team_attempt += 1
        game.current_leader_idx = (game.current_leader_idx + 1) % len(game.players)
        game.selected_team.clear()
        game.current_votes = {player: "❌" for player in game.players}
        page.pubsub.send_all("update")

    # ... (其餘邏輯保持不變) ...
    def route_change(route): build_current_view()
    page.on_route_change = route_change
    build_current_view()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0")
