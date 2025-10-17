# -*- coding: utf-8 -*-
"""Alias sem acentuação para o módulo `classificação_uscs`."""
from importlib import import_module as _import_module

_modulo_original = _import_module("app.modules.classificação_uscs")

globals().update({nome: getattr(_modulo_original, nome) for nome in dir(_modulo_original) if not nome.startswith("_")})

__all__ = [nome for nome in globals() if not nome.startswith("_")]
