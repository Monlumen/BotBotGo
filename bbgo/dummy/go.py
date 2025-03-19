from .Console import Console, WINDOW_MODE, CONSOLE_MODE
import debots

class GoObject():

    def __call__(self, query: str, n_rounds=1, n_available_workers=7, max_operations_webbot=30, display_mode=CONSOLE_MODE,
                 web_model=debots.cor_gemini_2_flash, draft_model=debots.cor_gemini_2_flash):
        console = Console()
        console.go(query, n_rounds=n_rounds, n_available_workers=n_available_workers,
                   max_operations_webbot=max_operations_webbot, display_mode=display_mode,
                   web_model=web_model, draft_model=draft_model)

    def __lshift__(self, query: str):
        assert isinstance(query, str)
        price_now = debots.read_cost()
        self.__call__(query)
        return debots.read_cost() - price_now

go = GoObject()