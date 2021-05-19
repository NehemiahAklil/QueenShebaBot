@echo off
TITLE Yui-Chan Bot
:: Enables virtual env mode and then execute auto restart yuii
env\scripts\activate.bat && nodemon -e py --exec \"python -m\" YuiiChan