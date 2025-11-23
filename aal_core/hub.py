import importlib
import logging
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List

import yaml

from .bus import Bus
from .models import ResonanceFrame

log = logging.getLogger(__name__)


@dataclass
class ModuleConfig:
    name: str
    path: str
    subscribe: List[str]
    publish: List[str]


class Hub:
    def __init__(self, config_path: str = "aal_core/config.yaml"):
        self.config_path = config_path
        self.bus: Bus | None = None
        self.modules: Dict[str, ModuleConfig] = {}
        self.handlers: Dict[str, List[Callable[[ResonanceFrame], None]]] = {}

    def load_config(self) -> None:
        with open(self.config_path, "r") as f:
            cfg = yaml.safe_load(f)

        self.bus = Bus(url=cfg["bus"]["url"])

        for m in cfg["modules"]:
            mc = ModuleConfig(
                name=m["name"],
                path=m["path"],
                subscribe=m.get("subscribe", []),
                publish=m.get("publish", []),
            )
            self.modules[mc.name] = mc

    def _load_module_callable(
        self, module_path: str
    ) -> Callable[[ResonanceFrame, Bus], List[ResonanceFrame]]:
        """
        Expect each module to expose a `handle_frame(frame, bus) -> list[ResonanceFrame]`.
        """
        mod = importlib.import_module(module_path)
        handler = getattr(mod, "handle_frame", None)
        if handler is None:
            raise RuntimeError(f"Module {module_path} missing handle_frame()")
        return handler

    def _subscribe(self, topic: str, handler: Callable[[ResonanceFrame], None]) -> None:
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)

        assert self.bus is not None
        # For simplicity, we spawn one thread per topic here.
        def listener():
            self.bus.subscribe(topic, handler)

        t = threading.Thread(target=listener, daemon=True)
        t.start()

    def start(self) -> None:
        self.load_config()
        assert self.bus is not None

        # Wire up modules
        for mc in self.modules.values():
            handler_fn = self._load_module_callable(mc.path)

            def make_handler(fn, module_name: str):
                def _h(frame: ResonanceFrame) -> None:
                    log.info("Module %s handling frame %s", module_name, frame.id)
                    out_frames = fn(frame, self.bus)
                    for of in out_frames or []:
                        # naive: broadcast to all module publish topics
                        for topic in self.modules[module_name].publish:
                            self.bus.publish(topic, of)
                return _h

            for topic in mc.subscribe:
                self._subscribe(topic, make_handler(handler_fn, mc.name))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    hub = Hub()
    hub.start()
    # Keep the main thread alive
    import time
    while True:
        time.sleep(1)
