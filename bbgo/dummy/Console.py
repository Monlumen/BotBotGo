import debots
from debots.tools.spawn_bots import DONT_PRINT, PRINT_TO_NEW_WINDOW
from ..kingbot import kingbot_ver0
from ..writer.Draft import Draft
import webbrowser
import os

CONSOLE_MODE = "CONSOLE_MODE"
WINDOW_MODE = "WINDOW_MODE"
DISPLAY_MODES = [CONSOLE_MODE, WINDOW_MODE]


# noinspection PyCallingNonCallable
class Console:
    def __init__(self, display_mode=WINDOW_MODE, verbal=True):
        self.kingbot = None
        self.draft = None
        self.verbal = verbal
        if self.verbal:
            print("BBGo Console 使用步骤:")
            print("1. 生成 draft. 通过 web_query 方法调查全网, 使用网络材料新建 draft. 或者通过 load_draft 方法从本地恢复 draft.")
            print("2. 完成 draft. 通过 finish_draft 方法实现. 这会使 draft 中的材料形成文章.")
            print("3. 备份 draft. 通过 save_draft 方法实现.")
            print("4. 编译 draft. 通过 compile_draft 方法, 将 draft 编译为 .html 文件.")

    def web_query(self, query:str, n_rounds=2, n_available_workers=3, max_operations_webbot=20, display_mode=WINDOW_MODE,
                  web_model=debots.cor_gpt4o_mini):
        if display_mode == WINDOW_MODE:
            debots.set_new_messages_verbal(False)
            kingbot_printer = print
            workers_print_type = PRINT_TO_NEW_WINDOW
        elif display_mode == CONSOLE_MODE:
            debots.set_new_messages_verbal(True)
            kingbot_printer = None
            workers_print_type = DONT_PRINT
        else:
            assert False
        self.kingbot = kingbot_ver0(
            n_rounds=n_rounds,
            n_available_workers=n_available_workers,
            enable_webbot=True,
            enable_filebot=False,
            enable_wikibot=False,
            max_operations_webbot=max_operations_webbot,
            kingbot_message_printer=kingbot_printer,
            workers_print_type=workers_print_type,
            webbot_auto_complete_saved_lines=False,
            kingbot_model=web_model,
            advisor_model=web_model,
            worker_model=web_model
        )
        self.kingbot.user_call(query)
        self.draft = Draft(king_history=self.kingbot.history, query=query)
        if self.verbal:
            print("BBGo Console: 调查结果 draft 已被加载到工作区. 接下来你可能想调用 finish_draft 方法")
        self.save_draft()

    def save_draft(self):
        saved_to = self.draft.save()
        if self.verbal:
            print(f"BBGo Console: 工作区的 draft 被保存到 {saved_to}")

    def load_draft(self, filepath):
        self.draft = Draft.load(filepath)
        if self.verbal:
            print(f"BBGo Console: 位于 {filepath} 的 draft 已被加载到工作区")

    def finish_draft(self, writer_model=None, translate=None, language=None,
                     translation_model=None):
        if not isinstance(self.draft, Draft):
            print(f"BBGo Console Error: 当前的工作区没有 draft")
            return
        if writer_model:
            self.draft.main_model = writer_model
        if language:
            self.draft.language = language
        if translate:
            self.draft.translate = translate
        if translation_model:
            self.draft.translation_model = translation_model

        if not self.draft.is_step_0_done():
            if self.verbal:
                print("BBGo Console: 工作区的 draft 正在完成 Step 0: Write outline")
            self.draft.step_0_write_outline()
        if not self.draft.is_step_1_done():
            if self.verbal:
                print("BBGo Console: 工作区的 draft 正在完成 Step 1: Stuff dimensions")
            self.draft.step_1_stuff_dimensions()
        if not self.draft.is_step_2_done():
            if self.verbal:
                print("BBGo Console: 工作区的 draft 正在完成 Step 2: Page meta")
            self.draft.step_2_page_meta()
        if not self.draft.is_step_3_done():
            if self.verbal:
                print("BBGo Console: 工作区的 draft 正在完成 Step 3: Dimension meta")
            self.draft.step_3_dim_meta()
        if not self.draft.is_step_4_done():
            if self.verbal:
                print("BBGo Console: 工作区的 draft 正在完成 Step 4: Translation")
            self.draft.step_4_translate()
        if not self.draft.is_step_5_done():
            if self.verbal:
                print("BBGo Console: 工作区的 draft 正在完成 Step 5: Refinement")
            self.draft.step_5_refinement()

        self.save_draft()

    def compile_draft(self, path="output_bitcoin.html"):
        if not isinstance(self.draft, Draft):
            print(f"BBGo Console Error: 当前的工作区没有 draft")
            return
        if not any(map(lambda x: x.rating, self.draft.lib)):
            print("BBGo Console Error: 请先调用 finish_draft")
            return
        success = self.draft.save_as_html(path)
        if success:
            if self.verbal:
                print(f"BBGo Console: 编译成功, html 已被储存到 {path}")
            webbrowser.open(os.path.abspath(path))
        if not success:
            print("BBGo Console Error: 编译失败")

    def go(self, query:str, n_rounds=2, n_available_workers=3, max_operations_webbot=20, display_mode=WINDOW_MODE,
           web_model=debots.cor_gpt4o_mini,
           draft_model=debots.openrouter_gemini_flash_2):
        self.web_query(query=query, n_rounds=n_rounds, n_available_workers=n_available_workers,
                       max_operations_webbot=max_operations_webbot, display_mode=display_mode,
                       web_model=web_model)
        self.finish_draft(writer_model=draft_model, translation_model=draft_model)
        self.compile_draft(query + ".html")