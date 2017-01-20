import numpy as np
import random 
import math

def init_pop(pop_size, node_num):
    population = []
    for i in range(pop_size):
        chrom = rand_init_seq(node_num)
        population.append(chrom)
    return population

def evolve(gen_max, generation, cross_prob, mutat_prob, node_num, weight_map):
    
    for k in range(gen_max):
        # Evaluate selection prob of current generation
        fitness, select_prob, weight = evaluate(generation, node_num, weight_map)
        #print fitness, select_prob
        if k % 1 == 0:
            weight = np.array(weight)
            fitness = np.array(fitness)
            print np.argmin(weight),np.argmax(weight)    
            print (k, max(weight), min(weight)) 
        
        # Evolve with genetic operations
        i = 0
        next_generation = []
        while True:
            print 'current:',generation        
            chrom1 = generation[select(select_prob)]
            chrom2 = generation[select(select_prob)]
            if chrom1 == chrom2:
                continue
            print 'selected:',chrom1,';', chrom2

             
            # Perform cross
            (chrom1, chrom2) = uniform_crossover(chrom1, chrom2, cross_prob) 
            print 'crossed:',chrom1,';', chrom2

            # Perform mutate
            max_val = node_num            
            chrom1 = mutate(chrom1, max_val, mutat_prob)
            chrom2 = mutate(chrom2, max_val, mutat_prob)
            print 'mutated:',chrom1,';', chrom2
            
                         
            # Generate next generation    
            next_generation.append(chrom1)
            next_generation.append(chrom2)
            i += 2
            # Check termination condition
            if i >= len(generation):
                break
        
        # Replace the current generation with next one
        #print 'next:',next_generation
        generation = next_generation

    fitness, select_prob, weight = evaluate(generation, node_num, weight_map)
    print 'Final:',fitness, weight#(k, max(weight), min(weight)) 
    weight = np.array(weight)
    fitness = np.array(fitness)
    print np.argmin(weight), np.argmax(fitness)
    
def evaluate(generation, node_num, weight_map):
    '''Evalutate the selection probability of each individual'''
    fitness = []
    weight = []
    select_prob = []
    for chrom in generation :
        fit_val, weight_val = eval_fitness(chrom, node_num, weight_map)
        fitness.append(fit_val)
        weight.append(weight_val)
    
    total = sum(fitness)
    for val in fitness:
        select_prob.append(val / total)
    
    # For Roulette Selection
    for i in range(1, len(select_prob)):
        select_prob[i] += select_prob[i-1] 
    return fitness, select_prob, weight

def rand_init_seq(node_num):
    seq = []
    for i in range(node_num-2):
        seq.append(random.randint(1, node_num))
    return seq

def eval_fitness(chrom, node_num, weight_map):
    """
    Fitness function of a prufer sequence by
    calculating total weight of edges of a spanning tree
    """
    chrom = list(chrom) # manipulate the content without affect original object
    tree, edges=prufer_to_tree(chrom, node_num)
    total = 0
    for e in edges:
        total += weight_map[e[0]][e[1]]

    fitness = 1 / (1 + total)
    return fitness, total

def select(select_prob):
    """
    Roulette wheel
    """
    t = random.random()
    i = 0 
    for p in select_prob:
        if p > t:
            break
        i += 1
    print 'select %d'%i
    return i

def uniform_crossover(chrom1, chrom2, cross_prob):
    length = len(chrom1)
    if chrom1 != chrom2 and random.random() < cross_prob:
        #print 'cross'
        mask = np.random.randint(2, size=length)
        for i in range(length):
            if mask[i] == 1:
                temp = chrom1[i]
                chrom1[i] = chrom2[i]
                chrom2[i] = temp
    return (chrom1, chrom2)

    
def mutate(chrom, max_val, mutat_prob):
    if random.random() < mutat_prob:
        #print 'mutate'
        inx = random.randint(0,len(chrom)-1)
        val = random.randint(1, max_val)
        chrom[inx] = val
    return chrom
	

def tree_to_prufer(tree):
    """
    Transform a spanning tree to correspondent prufer sequence
    Input: tree {node: [neighbours]}
    Return: prufer sequence as a list
    """
    p = []
    node_num = len(tree.keys())
    while len(tree.keys()) > 0:    
        # iterate from 1st indices
        for i in range(1, node_num+1):
            # if i is in a leaf edge
            if i in tree and len(tree[i]) == 1:
                j = tree[i][0]
                #print 'checking',(i,j)
                tree.pop(i)
                if len(tree[j]) > 1:
                    tree[j].remove(i)
                else:
                    tree.pop(j)
                # if it is not the last edge
                if len(tree.keys()) > 0:
                    p.append(j)
                break
    return p

def prufer_to_tree(pruf_seq, node_num):
    """
    Transform a prufer sequence to a spanning tree
    Input: prufer sequence as a list
    Return: tree {node: [neighbours]}, edges (node,node) as a list
    """
    p = list(pruf_seq)
    p_dual = []
    tree = {}     # presentation for prufer number transformation
    edges = []    # presentation for fitness calculation
    for i in range(1, node_num+1):
        # inital tree and pDual
        tree[i] = []
        if i not in p:
            p_dual.append(i)
    
    while len(p)>0:
        k = p[0]
        p_dual = sorted(p_dual, reverse=True)    
        j = p_dual.pop()
        edges.append((j,k))
        tree[j].append(k)
        tree[k].append(j)
        p.remove(k)
        if k not in p:
            p_dual.append(k)
    (j,k) = (p_dual.pop(),p_dual.pop())
    edges.append((j,k))
    tree[j].append(k)
    tree[k].append(j)
    
    return tree, edges

