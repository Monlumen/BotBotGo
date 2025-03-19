import debots

import concurrent.futures
from types import FunctionType
from threading import Thread
from queue import Queue

DONT_PRINT = "DONT_PRINT"
PRINT_TO_TERMINAL = "PRINT_TO_TERMINAL"
PRINT_TO_NEW_WINDOW = "PRINT_TO_NEW_WINDOW"

def get_spawn_bots_function(generator_name_pairs: [(FunctionType, str)],  # function是个无参函数,返回值是一个新建的bot
                            spawner: debots.Entity,
                            max_spawns_per_round: int=3,
                            max_rounds: int=2,
                            bots_print_type: str = DONT_PRINT
                            ):
    assert bots_print_type in [DONT_PRINT, PRINT_TO_TERMINAL, PRINT_TO_NEW_WINDOW]
    available_rounds = max_rounds

    def bot_as_a_function(bot_generator: FunctionType, instruction: str, name: str="", message_printer=None,
                        window_terminate = None,
                        results_queue = None,
                        instruction_inheritance=True) -> debots.Message:
        nonlocal spawner
        bot = bot_generator()
        bot.message_printer = message_printer
        if name:
            bot.name += f"({name})"
        try:
            if instruction_inheritance and hasattr(spawner, "last_prompt") and spawner.last_prompt:
                instruction = f'''(背景信息:{spawner.name}正在完成委托\"{spawner.last_prompt}\",并把以下子委托分给了你)
你分到的子委托:{instruction}'''
            message = debots.Message(spawner, bot, instruction)
            return_message = bot.delegate(message)
            if window_terminate is not None:
                window_terminate()
            if results_queue is not None:
                results_queue.put(return_message)
            return return_message
        except Exception as e:
            if window_terminate is not None:
                window_terminate()
            if results_queue is not None:
                results_queue.put(f"Error in bot {name}: {str(e)}")
            raise e

    def run_bots_in_parallel(generator_instruction_pairs) -> [debots.Message]:
        nonlocal spawner, bots_print_type
        if bots_print_type in [DONT_PRINT, PRINT_TO_TERMINAL]:
            message_printer = print if bots_print_type == PRINT_TO_TERMINAL else None
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(generator_instruction_pairs) * 3) as executor:
                futures = [executor.submit(bot_as_a_function, *pair, str(idx+1), message_printer) for idx, pair in enumerate(generator_instruction_pairs)]
                for future in concurrent.futures.as_completed(futures):
                    yield future.result()
        elif bots_print_type == PRINT_TO_NEW_WINDOW:
            controllers, mainloop = debots.get_tab_controllers_and_mainloop(len(generator_instruction_pairs))
            threads = []
            results_queue = Queue()
            for idx, pair in enumerate(generator_instruction_pairs):
                controllers[idx].set_title(f"Bot {idx+1}")
                controllers[idx].set_label("🤖: "+pair[1])
                threads.append(Thread(target=bot_as_a_function, args=(*pair, str(idx+1),
                                                                       controllers[idx].print,
                                                                       controllers[idx].terminate,
                                                                       results_queue)))
            for thread in threads:
                thread.start()
            mainloop()
            for thread in threads:
                thread.join()
            while not results_queue.empty():
                yield results_queue.get()

    def spawn_bots(instructions: str) -> str:
        nonlocal generator_name_pairs, spawner, max_spawns_per_round, available_rounds, max_rounds
        if available_rounds <= 0:
            return (f"You have reached the limit of {max_rounds} rounds for spawning bots. "
                    f"No more rounds are available.")
        instructions.replace(r"\\\n", "\n")
        instructions.replace(r"\\n", "\n")
        instructions.replace(r"\n", "\n")
        lines = instructions.strip().splitlines()
        generator_instruction_pairs = [] # [(FunctionType, str)]
        public_message = None
        for idx, line in enumerate(lines):
            line_splits = line.split(':', maxsplit=1)
            if len(line_splits) == 1:
                if idx == len(lines) - 1:
                    public_message = line
                else:
                    return f"Cannot parse this line: no colon found to separate the bot name and its instruction: {line}"
            if len(line_splits) == 2:
                bot_name, instruction = line_splits
                bot_name = bot_name.strip()
                found_the_bot = False
                for registered_generator, registered_bot_name in generator_name_pairs:
                    if bot_name.lower() == registered_bot_name.lower():
                        generator_instruction_pairs += [(registered_generator, instruction)]
                        found_the_bot = True
                        break
                if not found_the_bot:
                    return f"Can't find the bot {bot_name}. typo?"
        if len(generator_instruction_pairs) > max_spawns_per_round:
            return f"Maximum allowed bots: {max_spawns_per_round}. You attempted to spawn: {len(generator_instruction_pairs)}."
        if public_message:
            for idx in range(len(generator_instruction_pairs)):
                generator_instruction_pairs[idx] = (generator_instruction_pairs[idx][0],
                                              generator_instruction_pairs[idx][1] + "\nBackground Information:" + public_message)
        available_rounds -= 1  # 正式确定开跑
        for message in run_bots_in_parallel(generator_instruction_pairs):
            if hasattr(spawner, "log_message"):
                spawner.log_message(message)
        if available_rounds > 0:
            return (f"All bots have completed their tasks. "
                    f"You still have {available_rounds} rounds available for spawning.")
        else:
            return ("All bots have completed their tasks, "
                    "but you cannot spawn any more bots as all rounds have been used.")
    return spawn_bots