from numpy import *

def getMinVolEllipse(P, tolerance=0.01):
    """ Author:
    https://github.com/minillinim/ellipsoid
        """
    (N, d) = shape(P)
    d = float(d)
    
    # Q will be our working array
    Q = vstack([copy(P.T), ones(N)]) 
    QT = Q.T
        
    # initializations
    err = 1.0 + tolerance
    u = (1.0 / N) * ones(N)

    # Khachiyan Algorithm
    while err > tolerance:
        V = dot(Q, dot(diag(u), QT))
        M = diag(dot(QT , dot(linalg.inv(V), Q)))    # M the diagonal vector of an NxN matrix
        j = argmax(M)
        maximum = M[j]
        step_size = (maximum - d - 1.0) / ((d + 1.0) * (maximum - 1.0))
        new_u = (1.0 - step_size) * u
        new_u[j] += step_size
        err = linalg.norm(new_u - u)
        u = new_u

        # center of the ellipse 
        center = dot(P.T, u)
        
        # the A matrix for the ellipse
        A = linalg.inv(
            dot(P.T, dot(diag(u), P)) - 
            array([[a * b for b in center] for a in center])
        ) / d
        
        # Get the values we'd like to return
        U, s, rotation = linalg.svd(A)
        radii = 1.0/sqrt(s)
        
    return (center, radii, rotation)

