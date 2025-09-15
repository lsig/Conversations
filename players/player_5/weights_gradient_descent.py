import subprocess
import numpy as np



def weights_gradient_descent(weights, args, learning_rate=0.01, ):
    """Update weights using gradient descent."""


    subprocess.run(["uv", "run", "python", "main.py"] + args)

    return weights - learning_rate * gradients
