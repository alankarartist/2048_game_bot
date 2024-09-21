# 2048 Game Bot

This project is a bot for playing the 2048 game. The bot is implemented as a Dockerized HTTP server that listens on port 5000 and receives the game state in a query parameter. It then returns the best move (up, down, left, or right) using Monte Carlo simulations.

## Features

- Uses Monte Carlo Tree Search (MCTS) to determine the best move for each game state.
- Exposes a simple HTTP API for interacting with the bot.
- Dockerized for easy setup and deployment.

## Prerequisites

- Docker
- Docker Compose

## Getting Started

### Clone the repository

```bash
git clone https://github.com/alankarartist/2048_game_bot.git
cd 2048_game_bot
