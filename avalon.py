import flet as ft
import os

# 阿瓦隆各人數局的任務所需人數矩陣
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
        
        # -------------------------------------------------------------
        # 看板端視圖 (/board)
        # -------------------------------------------------------------
        if page.route == "/board":
            if not game.is_setup_complete:
                page.views.append(
                    ft.View(
                        route="/board", # 【語法修復】明確指定 route
                        controls=[
                            ft.Text("阿瓦隆全域歷史戰報看板", size=24, color=ft.Colors.WHITE70, weight=ft.FontWeight.BOLD),
                            ft.Divider(color=ft.Colors.WHITE24),
                            ft.Container(
                                content=ft.Text("等待書記端設定遊戲人數並開始遊戲...", color=ft.Colors.WHITE38, size=20),
                                padding=50,
                                alignment=ft.Alignment.CENTER
                            )
                        ],
                        bgcolor=ft.Colors.BLACK
                    )
                )
            else:
                page.views.append(
                    ft.View(
                        route="/board", # 【語法修復】明確指定 route
                        controls=[
                            ft.Text(f"阿瓦隆戰報看板 ({game.total_players}人局)", size=24, color=ft.Colors.WHITE70, weight=ft.FontWeight.BOLD),
                            ft.Divider(color=ft.Colors.WHITE24),
                            create_board_table(),
                        ],
                        bgcolor=ft.Colors.BLACK
                    )
                )
            
        # -------------------------------------------------------------
        # 控制器端視圖 (/admin 或預設)
        # -------------------------------------------------------------
        else:
            if not game.is_setup_complete:
                page.views.append(
                    ft.View(
                        route="/admin", # 【語法修復】明確指定 route
                        controls=[
                            ft.Text("⚙️ 遊戲初始設定", size=24, color=ft.Colors.WHITE70, weight=ft.FontWeight.BOLD),
                            ft.Divider(color=ft.Colors.WHITE24),
                            ft.Text("請選擇本局玩家總數：", color=ft.Colors.WHITE54, size=16),
                            create_setup_controls(),
                        ],
                        bgcolor=ft.Colors.BLACK
                    )
                )
            else:
                required_team_size = MISSION_SIZES[game.total_players][game.current_mission - 1]
                is_fifth_attempt = game.current_team_attempt == 5
                
                submit_btn_text = "🚨 強制執行並結算" if is_fifth_attempt else "結算送出"
                submit_btn_color = ft.Colors.RED_900 if is_fifth_attempt else ft.Colors.BLUE_GREY_900

                page.views.append(
                    ft.View(
                        route="/admin", # 【語法修復】明確指定 route
                        appbar=ft.AppBar(
                            title=ft.Text(f"任務 {game.current_mission} - 第 {game.current_team_attempt} 次派票", size=18, color=ft.Colors.WHITE70),
                            bgcolor=ft.Colors.BLACK,
                            actions=[
                                ft.TextButton(
                                    "重新開始",
                                    icon=ft.Icons.RESTART_ALT,
                                    icon_color=ft.Colors.RED_400,
                                    style=ft.ButtonStyle(color=ft.Colors.RED_400),
                                    on_click=confirm_reset_game
                                )
                            ]
                        ),
                        controls=[
                            ft.Row([
                                ft.Text(f"當前隊長：{game.players[game.current_leader_idx]}", size=14, color=ft.Colors.WHITE38),
                                ft.Text(f"應派人數：{required_team_size} 人 (已選: {len(game.selected_team)})", 
                                        size=14, 
                                        color=ft.Colors.AMBER_400 if len(game.selected_team) != required_team_size else ft.Colors.GREEN_400,
                                        weight=ft.FontWeight.BOLD)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Divider(color=ft.Colors.WHITE24),
                            
                            create_admin_controls(),
                            ft.Divider(color=ft.Colors.WHITE10),
                            
                            ft.Row([
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.UNDO,
                                        tooltip="復原上一步",
                                        on_click=undo_last_action,
                                        disabled=len(game.history) == 0,
                                        icon_color=ft.Colors.WHITE70,
                                        bgcolor=ft.Colors.GREY_900,
                                        icon_size=24,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.REDO,
                                        tooltip="取消復原 (重做)",
                                        on_click=redo_action,
                                        disabled=len(game.redo_stack) == 0,
                                        icon_color=ft.Colors.WHITE70,
                                        bgcolor=ft.Colors.GREY_900,
                                        icon_size=24,
                                    )
                                ], spacing=10),
                                
                                ft.ElevatedButton(
                                    submit_btn_text,
                                    on_click=process_voting_result,
                                    style=ft.ButtonStyle(
                                        bgcolor=submit_btn_color, 
                                        color=ft.Colors.WHITE,
                                        padding=ft.Padding(left=30, top=15, right=30, bottom=15),
                                    ),
                                    height=60,
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ],
                        bgcolor=ft.Colors.BLACK
                    )
                )
        page.update()

    def create_setup_controls():
        player_dropdown = ft.Dropdown(
            value="5",
            options=[ft.dropdown.Option(str(i)) for i in range(5, 11)],
            width=150,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREY_900
        )
        
        def on_start_click(e):
            game.start_game(int(player_dropdown.value))
            page.pubsub.send_all("update")
            
        return ft.Column([
            player_dropdown,
            ft.Container(height=20),
            ft.ElevatedButton(
                "確認並建立遊戲",
                on_click=on_start_click,
                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            )
        ])

    def create_admin_controls():
        controls_list = []
        is_fifth_attempt = game.current_team_attempt == 5

        for player in game.players:
            def make_vote_handler(p=player):
                return lambda e: toggle_vote(p)
                
            def make_team_handler(p=player):
                return lambda e: toggle_team(p)

            is_in_team = player in game.selected_team
            vote_status = game.current_votes[player]
            
            if is_fifth_attempt:
                vote_ui = ft.Text("🚨 強制", color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD, width=80, text_align=ft.TextAlign.RIGHT)
            else:
                vote_ui = ft.TextButton(f"投票: {vote_status}", on_click=make_vote_handler(), width=80)

            row = ft.Row([
                ft.Text(player, size=16, expand=True, color=ft.Colors.WHITE54),
                ft.Checkbox(label="出任務", value=is_in_team, on_change=make_team_handler()),
                vote_ui,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            controls_list.append(row)
            
        return ft.Column(controls_list, spacing=15)

    def create_board_table():
        if not game.history:
            return ft.Container(
                content=ft.Text("等待第一輪投票結果...", color=ft.Colors.WHITE38),
                padding=50
            )
            
        columns = [
            ft.DataColumn(ft.Text("局-次")),
            ft.DataColumn(ft.Text("隊長")),
            ft.DataColumn(ft.Text("結果")),
        ]
        for player in game.players:
            columns.append(ft.DataColumn(ft.Text(player)))
            
        rows = []
        for h in game.history:
            status_color = ft.Colors.WHITE54
            if "成功" in h["status"]: status_color = ft.Colors.BLUE_400
            elif "失敗" in h["status"]: status_color = ft.Colors.RED_400
            elif h["status"] == "否決": status_color = ft.Colors.GREY_600

            cells = [
                ft.DataCell(ft.Text(h["round"], color=ft.Colors.WHITE70)),
                ft.DataCell(ft.Text(h["leader"], color=ft.Colors.WHITE54)),
                ft.DataCell(ft.Text(h["status"], color=status_color, weight=ft.FontWeight.BOLD)),
            ]
            
            for player in game.players:
                vote = h["votes"].get(player, "-")
                is_in_team = player in h["team"]
                
                if vote == "⭕":
                    bg_color = ft.Colors.WHITE
                    icon_color = ft.Colors.RED
                elif vote == "❌":
                    bg_color = ft.Colors.GREY_900
                    icon_color = ft.Colors.RED
                else:
                    bg_color = ft.Colors.GREY_900
                    icon_color = ft.Colors.RED
                
                if is_in_team:
                    display_content = ft.Icon(ft.Icons.LOCAL_POLICE, color=icon_color, size=20)
                else:
                    display_content = ft.Container()
                
                cells.append(
                    ft.DataCell(
                        ft.Container(
                            content=display_content,
                            bgcolor=bg_color,
                            width=40,
                            height=30,
                            border_radius=4,
                            alignment=ft.Alignment.CENTER
                        )
                    )
                )
            rows.append(ft.DataRow(cells=cells))
            
        return ft.DataTable(columns=columns, rows=rows)

    def toggle_vote(player):
        current = game.current_votes[player]
        game.current_votes[player] = "⭕" if current == "❌" else "❌"
        build_current_view()

    def toggle_team(player):
        if player in game.selected_team:
            game.selected_team.remove(player)
        else:
            game.selected_team.add(player)
        build_current_view()

    def undo_last_action(e):
        if not game.history: return
        last_record = game.history.pop()
        game.redo_stack.append(last_record)
        
        mission_str, attempt_str = last_record["round"].split("-")
        game.current_mission = int(mission_str)
        game.current_team_attempt = int(attempt_str)
        game.current_leader_idx = game.players.index(last_record["leader"])
        game.selected_team = set(last_record["team"])
        game.current_votes = last_record["votes"].copy()
        page.pubsub.send_all("update")

    def redo_action(e):
        if not game.redo_stack: return
        record = game.redo_stack.pop()
        game.history.append(record)
        
        if "成功" in record["status"] or "失敗" in record["status"]:
            game.current_mission = int(record["round"].split("-")[0]) + 1
            game.current_team_attempt = 1
        else:
            game.current_mission = int(record["round"].split("-")[0])
            game.current_team_attempt = int(record["round"].split("-")[1]) + 1
            
        game.current_leader_idx = (game.players.index(record["leader"]) + 1) % len(game.players)
        game.selected_team.clear()
        game.current_votes = {player: "❌" for player in game.players}
        page.pubsub.send_all("update")

    def confirm_reset_game(e):
        def do_reset(e):
            game.reset_game()
            page.close(reset_dlg)
            page.pubsub.send_all("update")

        reset_dlg = ft.AlertDialog(
            title=ft.Text("⚠️ 重新開始遊戲"),
            content=ft.Text("確定要結束當前遊戲並重新開始嗎？\n大螢幕與手機端的所有歷史紀錄將會被清空！"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.close(reset_dlg)),
                ft.TextButton("確定重來", on_click=do_reset, style=ft.ButtonStyle(color=ft.Colors.RED_400)),
            ],
            bgcolor=ft.Colors.GREY_900,
        )
        page.open(reset_dlg)

    def process_voting_result(e):
        required_team_size = MISSION_SIZES[game.total_players][game.current_mission - 1]
        if len(game.selected_team) != required_team_size:
            err_dlg = ft.AlertDialog(
                title=ft.Text("⚠️ 任務人數錯誤"),
                content=ft.Text(f"第 {game.current_mission} 個任務必須派出 {required_team_size} 人！\n您目前勾選了 {len(game.selected_team)} 人。"),
                actions=[ft.TextButton("我知道了", on_click=lambda e: page.close(err_dlg))],
                bgcolor=ft.Colors.GREY_900
            )
            page.open(err_dlg)
            return

        if game.current_team_attempt == 5:
            for p in game.current_votes:
                game.current_votes[p] = "-"
            show_mission_result_dialog()
            return

        approve_count = sum(1 for v in game.current_votes.values() if v == "⭕")
        reject_count = sum(1 for v in game.current_votes.values() if v == "❌")

        if approve_count > reject_count:
            show_mission_result_dialog()
        else:
            finalize_round("否決")

    def show_mission_result_dialog():
        max_fails = len(game.selected_team) if game.selected_team else 0
        
        fail_dropdown = ft.Dropdown(
            label="出現幾張失敗票？",
            value="0",
            options=[ft.dropdown.Option(str(i)) for i in range(max_fails + 1)],
            width=150,
            bgcolor=ft.Colors.GREY_800,
            color=ft.Colors.WHITE
        )

        def on_result_submit(e):
            fail_count = int(fail_dropdown.value)
            
            if fail_count == 0:
                final_status = "成功"
            elif fail_count == 1:
                if game.total_players >= 7 and game.current_mission == 4:
                    final_status = "成功 (1敗)"
                else:
                    final_status = "失敗 (1敗)"
            else:
                final_status = f"失敗 ({fail_count}敗)"
                
            page.close(dlg)
            finalize_round(final_status)

        dlg = ft.AlertDialog(
            title=ft.Text("🚀 任務出發！"),
            content=ft.Column([
                ft.Text("任務已啟動，請結算卡牌："),
                fail_dropdown
            ], tight=True),
            actions=[
                ft.TextButton("確認結算", on_click=on_result_submit, style=ft.ButtonStyle(color=ft.Colors.BLUE_400)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=ft.Colors.GREY_900
        )
        page.open(dlg)

    def finalize_round(mission_status):
        round_tag = f"{game.current_mission}-{game.current_team_attempt}"
        leader_name = game.players[game.current_leader_idx]
        
        game.history.append({
            "round": round_tag,
            "leader": leader_name,
            "team": list(game.selected_team),
            "votes": game.current_votes.copy(),
            "status": mission_status 
        })
        
        game.redo_stack.clear()
        
        if "成功" in mission_status or "失敗" in mission_status:
            game.current_mission += 1      
            game.current_team_attempt = 1  
        else:
            game.current_team_attempt += 1 
            
        game.current_leader_idx = (game.current_leader_idx + 1) % len(game.players)
        game.selected_team.clear()
        
        game.current_votes = {player: "❌" for player in game.players}
        
        page.pubsub.send_all("update")

    def route_change(route):
        build_current_view()

    page.on_route_change = route_change
    build_current_view()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")
