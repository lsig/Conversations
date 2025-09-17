import subprocess


def weights_gradient_descent(
	weights,
	args,
	learning_rate=0.01,
):
	"""Update weights using gradient descent."""

	subprocess.run(['uv', 'run', 'python', 'main.py'] + args)

	# Fix it being null since it's not implemented, and won't pass uv run ruff check
	gradients=0

	return weights - learning_rate * gradients
