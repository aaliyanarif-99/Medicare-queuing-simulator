import math
import random
from decimal import Decimal, localcontext
import tkinter as tk
from tkinter import ttk, messagebox, END, BOTH, X, Y, HORIZONTAL, VERTICAL, LEFT, RIGHT, NW
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from statistics import mean

random.seed(0)


def generate_general_arrivals(n, mean_arrival, arrival_dist="normal", a_arr=None, b_arr=None):
    inter_arrivals = []
    if arrival_dist == "exponential":
        for _ in range(n): inter_arrivals.append(random.expovariate(1.0 / mean_arrival))
    elif arrival_dist == "normal":
        for _ in range(n):
            v = max(0.1, random.gauss(mean_arrival, max(0.001, mean_arrival / 3.0)))
            inter_arrivals.append(v)
    elif arrival_dist == "uniform":
        a = a_arr if a_arr is not None else 0.5 * mean_arrival
        b = b_arr if b_arr is not None else 1.5 * mean_arrival
        for _ in range(n):
            v = a + (b - a) * random.random()
            inter_arrivals.append(v)
    elif arrival_dist == "lognormal":
        sigma = 0.6
        mu = math.log(max(1e-6, mean_arrival)) - 0.5 * sigma ** 2
        for _ in range(n):
            v = random.lognormvariate(mu, sigma)
            inter_arrivals.append(v)
    elif arrival_dist == "gamma":
        shape = 2.0
        scale = mean_arrival / shape
        for _ in range(n):
            v = random.gammavariate(shape, max(1e-6, scale))
            inter_arrivals.append(v)
    else:
        for _ in range(n): inter_arrivals.append(random.expovariate(1.0 / mean_arrival))
    inter_arrivals = [max(1, int(round(v))) for v in inter_arrivals]
    arrival_times = [inter_arrivals[0]]
    for i in range(1, n): arrival_times.append(arrival_times[i - 1] + inter_arrivals[i])
    return inter_arrivals, arrival_times

def generate_arrivals_by_cp(mean_arrival):
    cumulative = 0.0
    cp = []
    k = 0
    while cumulative < 0.99999:
        with localcontext() as ctx:
            ctx.prec = 20
            prob = (Decimal(math.exp(-mean_arrival)) * ctx.power(Decimal(mean_arrival), k)) / math.factorial(k)
            cumulative += float(prob)
            cp.append(float(cumulative))
        k += 1
    n = len(cp)
    cp_lookup = [0.0] + cp[:-1]
    avg_times = list(range(n))
    inter_arrivals = []
    for _ in range(n):
        r = random.random()
        for kk, cval in enumerate(cp):
            if r <= cval:
                inter_arrivals.append(kk)
                break
    if inter_arrivals: inter_arrivals[0] = 0
    arrival_times = [inter_arrivals[0]]
    for i in range(1, n): arrival_times.append(arrival_times[i - 1] + inter_arrivals[i])
    return cp, cp_lookup, avg_times, inter_arrivals, arrival_times

def generate_service_times(n, mean_service, dist_type="normal", a=None, b=None):
    out = []
    for _ in range(n):
        if mean_service is not None and mean_service <= 0:
            out.append(1)
        else:
            if dist_type == "normal":
                base_mean = mean_service if mean_service is not None else 1.0
                v = max(0.1, random.gauss(base_mean, max(0.001, base_mean / 3.0)))
            elif dist_type == "uniform":
                if a is not None and b is not None:
                    v = a + (b - a) * random.random()
                else:
                    base_mean = mean_service if mean_service is not None else 1.0
                    v = random.uniform(0.5 * base_mean, 1.5 * base_mean)
            elif dist_type == "lognormal":
                sigma = 0.6
                base_mean = mean_service if mean_service is not None else 1.0
                mu = math.log(max(1e-6, base_mean)) - 0.5 * sigma ** 2
                v = random.lognormvariate(mu, sigma)
            elif dist_type == "gamma":
                shape = 2.0
                base_mean = mean_service if mean_service is not None else 1.0
                scale = base_mean / shape
                v = random.gammavariate(shape, max(1e-6, scale))
            else:
                base_mean = mean_service if mean_service is not None else 1.0
                v = random.expovariate(1.0 / base_mean)
            out.append(max(1, int(round(v))))
    return out

def generate_priorities(n, low=1, high=3):
    return [random.randint(low, high) for _ in range(n)]

class Patient:
    def __init__(self, pid, arrival, service, priority=None):
        self.id = pid
        self.arrival = int(arrival)
        self.service = int(service)
        self.remaining = int(service)
        self.priority = int(priority) if priority is not None else None
        self.first_start = None
        self.end = None
        self.turnaround = None
        self.wait = None
        self.response = None
        self.preferred_server = None
        self.segments = []
    def start_on(self, server_id, t):
        t = int(t)
        if self.first_start is None:
            self.first_start = t
            self.response = t - self.arrival
        self.segments.append([server_id, t, None])
    def stop_at(self, t):
        t = int(t)
        if self.segments and self.segments[-1][2] is None:
            self.segments[-1][2] = t
    def finalize(self, t):
        t = int(t)
        self.end = t
        self.turnaround = self.end - self.arrival
        self.wait = max(0, self.turnaround - self.service)
        if self.response is None:
            self.response = 0

def simulate_ggs_preemptive(mean_arrival, mean_service, servers_count=1, pr_range=(1, 3), arrival_dist="normal", service_dist="normal", a_arr=None, b_arr=None, a_serv=None, b_serv=None):
    n = random.randint(15,25)
    inter_arr, arrivals = generate_general_arrivals(n, mean_arrival, arrival_dist, a_arr, b_arr)
    services = generate_service_times(n, mean_service, service_dist, a_serv, b_serv)
    priorities = generate_priorities(n, pr_range[0], pr_range[1])
    patients = [Patient(i + 1, arrivals[i], services[i], priorities[i]) for i in range(n)]
    servers = [{'p': None, 'end': None} for _ in range(servers_count)]
    waiting = []
    arrival_idx = 0
    timeline = []
    queue_lengths = []
    util_over_time = []
    def next_arrival_time(): return patients[arrival_idx].arrival if arrival_idx < n else math.inf
    def next_completion_time():
        times = [s['end'] for s in servers if s['p'] is not None]
        return min(times) if times else math.inf
    while True:
        ta = next_arrival_time()
        tc = next_completion_time()
        if ta == tc == math.inf:
            break
        if ta <= tc:
            t = ta
            arrivals_at_t = []
            while arrival_idx < n and patients[arrival_idx].arrival == t:
                arrivals_at_t.append(patients[arrival_idx])
                arrival_idx += 1
            arrivals_at_t.sort(key=lambda p: (p.priority, p.arrival, p.id))
            for newp in arrivals_at_t:
                candidate_sid = None
                worst_priority = -math.inf
                for sid, s in enumerate(servers):
                    if s['p'] is not None and s['p'].priority > newp.priority:
                        if s['p'].priority > worst_priority:
                            worst_priority = s['p'].priority
                            candidate_sid = sid
                if candidate_sid is not None:
                    running = servers[candidate_sid]['p']
                    running.stop_at(t)
                    seg_start = running.segments[-1][1]
                    consumed = int(t) - int(seg_start)
                    running.remaining = max(0, running.remaining - consumed)
                    running.preferred_server = candidate_sid + 1
                    if running.remaining > 0:
                        waiting.append(running)
                    servers[candidate_sid] = {'p': None, 'end': None}
                    newp.start_on(candidate_sid + 1, t)
                    servers[candidate_sid]['p'] = newp
                    servers[candidate_sid]['end'] = t + newp.remaining
                else:
                    free_sid = next((sid for sid, s in enumerate(servers) if s['p'] is None), None)
                    if free_sid is not None:
                        newp.start_on(free_sid + 1, t)
                        servers[free_sid]['p'] = newp
                        servers[free_sid]['end'] = t + newp.remaining
                    else:
                        waiting.append(newp)
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pref_cands = [p for p in waiting if p.preferred_server == sid + 1]
                        if pref_cands:
                            pref_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                            pick = pref_cands[0]
                            waiting.remove(pick)
                        else:
                            free_cands = [p for p in waiting if p.preferred_server is None]
                            if free_cands:
                                free_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                                pick = free_cands[0]
                                waiting.remove(pick)
                            else:
                                continue
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        else:
            t = tc
            for sid, s in enumerate(servers):
                if s['p'] is not None and s['end'] == t:
                    p = s['p']
                    p.stop_at(t)
                    seg_start = p.segments[-1][1]
                    consumed = int(t) - int(seg_start)
                    p.remaining = max(0, p.remaining - consumed)
                    p.finalize(t)
                    servers[sid] = {'p': None, 'end': None}
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pref_cands = [p for p in waiting if p.preferred_server == sid + 1]
                        if pref_cands:
                            pref_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                            pick = pref_cands[0]
                            waiting.remove(pick)
                        else:
                            free_cands = [p for p in waiting if p.preferred_server is None]
                            if free_cands:
                                free_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                                pick = free_cands[0]
                                waiting.remove(pick)
                            else:
                                continue
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        busy_count = sum(1 for s in servers if s['p'] is not None)
        timeline.append(t)
        queue_lengths.append(len(waiting))
        util_over_time.append(busy_count / servers_count if servers_count > 0 else 0)
    last_completion = 0
    for p in patients:
        if p.end is None:
            if p.first_start is None:
                p.first_start = p.arrival
                p.response = 0
            p.end = p.first_start + p.service
            p.finalize(p.end)
        if p.end > last_completion: last_completion = p.end
    segments = {sid + 1: [] for sid in range(servers_count)}
    for p in patients:
        for seg in p.segments:
            sid, st, en = seg[0], seg[1], seg[2] if seg[2] is not None else seg[1]
            segments[sid].append((p.id, int(st), int(en)))
    for sid in segments: segments[sid].sort(key=lambda s: s[1])
    server_busy_raw = {sid: sum(en - st for _, st, en in segments[sid]) for sid in segments}
    last_completion = max(1, last_completion)
    util_map = {sid: server_busy_raw.get(sid, 0) / last_completion for sid in range(1, servers_count + 1)}
    total_busy = sum(server_busy_raw.values())
    if total_busy > 0:
        util_share_map = {sid: server_busy_raw.get(sid, 0) / total_busy for sid in range(1, servers_count + 1)}
    else:
        util_share_map = {sid: 1.0 / max(1, servers_count) for sid in range(1, servers_count + 1)}
    avg_util = sum(util_map.values()) / max(1, len(util_map))
    return {'patients': patients, 'segments': segments, 'util_map': util_map, 'util_share_map': util_share_map, 'avg_util': avg_util, 'T': max(1, last_completion), 'inter_arr': inter_arr, 'arrivals': arrivals, 'services': services, 'timeline': timeline, 'queue': queue_lengths, 'arrival_dist': arrival_dist, 'service_dist': service_dist}

def simulate_ggs_nonpreemptive(mean_arrival, mean_service, servers_count=1, arrival_dist="normal", service_dist="normal", a_arr=None, b_arr=None, a_serv=None, b_serv=None):
    n = random.randint(15,25)
    inter_arr, arrivals = generate_general_arrivals(n, mean_arrival, arrival_dist, a_arr, b_arr)
    services = generate_service_times(n, mean_service, service_dist, a_serv, b_serv)
    patients = [Patient(i + 1, arrivals[i], services[i], priority=None) for i in range(n)]
    servers = [{'p': None, 'end': None} for _ in range(servers_count)]
    waiting = []
    arrival_idx = 0
    timeline = []
    queue_lengths = []
    util_over_time = []
    def next_arrival_time(): return patients[arrival_idx].arrival if arrival_idx < n else math.inf
    def next_completion_time():
        times = [s['end'] for s in servers if s['p'] is not None]
        return min(times) if times else math.inf
    while True:
        ta = next_arrival_time()
        tc = next_completion_time()
        if ta == tc == math.inf:
            break
        if ta <= tc:
            t = ta
            arrivals_at_t = []
            while arrival_idx < n and patients[arrival_idx].arrival == t:
                arrivals_at_t.append(patients[arrival_idx])
                arrival_idx += 1
            for newp in arrivals_at_t:
                free_sid = next((sid for sid, s in enumerate(servers) if s['p'] is None), None)
                if free_sid is not None:
                    newp.start_on(free_sid + 1, t)
                    servers[free_sid]['p'] = newp
                    servers[free_sid]['end'] = t + newp.remaining
                else:
                    waiting.append(newp)
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pick = waiting.pop(0)
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        else:
            t = tc
            for sid, s in enumerate(servers):
                if s['p'] is not None and s['end'] == t:
                    p = s['p']
                    p.stop_at(t)
                    seg_start = p.segments[-1][1]
                    consumed = int(t) - int(seg_start)
                    p.remaining = max(0, p.remaining - consumed)
                    p.finalize(t)
                    servers[sid] = {'p': None, 'end': None}
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pick = waiting.pop(0)
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        busy_count = sum(1 for s in servers if s['p'] is not None)
        timeline.append(t)
        queue_lengths.append(len(waiting))
        util_over_time.append(busy_count / servers_count if servers_count > 0 else 0)
    last_completion = 0
    for p in patients:
        if p.end is None:
            if p.first_start is None:
                p.first_start = p.arrival
                p.response = 0
            p.end = p.first_start + p.service
            p.finalize(p.end)
        if p.end > last_completion: last_completion = p.end
    segments = {sid + 1: [] for sid in range(servers_count)}
    for p in patients:
        for seg in p.segments:
            sid, st, en = seg[0], seg[1], seg[2] if seg[2] is not None else seg[1]
            segments[sid].append((p.id, int(st), int(en)))
    for sid in segments: segments[sid].sort(key=lambda s: s[1])
    server_busy_raw = {sid: sum(en - st for _, st, en in segments[sid]) for sid in segments}
    last_completion = max(1, last_completion)
    util_map = {sid: server_busy_raw.get(sid, 0) / last_completion for sid in range(1, servers_count + 1)}
    total_busy = sum(server_busy_raw.values())
    if total_busy > 0:
        util_share_map = {sid: server_busy_raw.get(sid, 0) / total_busy for sid in range(1, servers_count + 1)}
    else:
        util_share_map = {sid: 1.0 / max(1, servers_count) for sid in range(1, servers_count + 1)}
    avg_util = sum(util_map.values()) / max(1, len(util_map))
    return {'patients': patients, 'segments': segments, 'util_map': util_map, 'util_share_map': util_share_map, 'avg_util': avg_util, 'T': max(1, last_completion), 'inter_arr': inter_arr, 'arrivals': arrivals, 'services': services, 'timeline': timeline, 'queue': queue_lengths, 'arrival_dist': arrival_dist, 'service_dist': service_dist}

def simulate_preemptive_v5(mean_arrival, mean_service, servers_count=1, pr_range=(1, 3), dist_type="normal", a=None, b=None):
    cp, cp_lookup, avg_times, inter_arr, arrivals = generate_arrivals_by_cp(mean_arrival)
    n = len(arrivals)
    services = generate_service_times(n, mean_service, dist_type, a=a, b=b)
    priorities = generate_priorities(n, pr_range[0], pr_range[1])
    patients = [Patient(i + 1, arrivals[i], services[i], priorities[i]) for i in range(n)]
    servers = [{'p': None, 'end': None} for _ in range(servers_count)]
    waiting = []
    arrival_idx = 0
    timeline = []
    queue_lengths = []
    util_over_time = []
    def next_arrival_time(): return patients[arrival_idx].arrival if arrival_idx < n else math.inf
    def next_completion_time():
        times = [s['end'] for s in servers if s['p'] is not None]
        return min(times) if times else math.inf
    while True:
        ta = next_arrival_time()
        tc = next_completion_time()
        if ta == tc == math.inf:
            break
        if ta <= tc:
            t = ta
            arrivals_at_t = []
            while arrival_idx < n and patients[arrival_idx].arrival == t:
                arrivals_at_t.append(patients[arrival_idx])
                arrival_idx += 1
            arrivals_at_t.sort(key=lambda p: (p.priority, p.arrival, p.id))
            for newp in arrivals_at_t:
                candidate_sid = None
                worst_priority = -math.inf
                for sid, s in enumerate(servers):
                    if s['p'] is not None and s['p'].priority > newp.priority:
                        if s['p'].priority > worst_priority:
                            worst_priority = s['p'].priority
                            candidate_sid = sid
                if candidate_sid is not None:
                    running = servers[candidate_sid]['p']
                    running.stop_at(t)
                    seg_start = running.segments[-1][1]
                    consumed = int(t) - int(seg_start)
                    running.remaining = max(0, running.remaining - consumed)
                    running.preferred_server = candidate_sid + 1
                    if running.remaining > 0:
                        waiting.append(running)
                    servers[candidate_sid] = {'p': None, 'end': None}
                    newp.start_on(candidate_sid + 1, t)
                    servers[candidate_sid]['p'] = newp
                    servers[candidate_sid]['end'] = t + newp.remaining
                else:
                    free_sid = next((sid for sid, s in enumerate(servers) if s['p'] is None), None)
                    if free_sid is not None:
                        newp.start_on(free_sid + 1, t)
                        servers[free_sid]['p'] = newp
                        servers[free_sid]['end'] = t + newp.remaining
                    else:
                        waiting.append(newp)
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pref_cands = [p for p in waiting if p.preferred_server == sid + 1]
                        if pref_cands:
                            pref_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                            pick = pref_cands[0]
                            waiting.remove(pick)
                        else:
                            free_cands = [p for p in waiting if p.preferred_server is None]
                            if free_cands:
                                free_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                                pick = free_cands[0]
                                waiting.remove(pick)
                            else:
                                continue
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        else:
            t = tc
            for sid, s in enumerate(servers):
                if s['p'] is not None and s['end'] == t:
                    p = s['p']
                    p.stop_at(t)
                    seg_start = p.segments[-1][1]
                    consumed = int(t) - int(seg_start)
                    p.remaining = max(0, p.remaining - consumed)
                    p.finalize(t)
                    servers[sid] = {'p': None, 'end': None}
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pref_cands = [p for p in waiting if p.preferred_server == sid + 1]
                        if pref_cands:
                            pref_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                            pick = pref_cands[0]
                            waiting.remove(pick)
                        else:
                            free_cands = [p for p in waiting if p.preferred_server is None]
                            if free_cands:
                                free_cands.sort(key=lambda p: (p.priority, p.arrival, p.id))
                                pick = free_cands[0]
                                waiting.remove(pick)
                            else:
                                continue
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        busy_count = sum(1 for s in servers if s['p'] is not None)
        timeline.append(t)
        queue_lengths.append(len(waiting))
        util_over_time.append(busy_count / servers_count if servers_count > 0 else 0)
    last_completion = 0
    for p in patients:
        if p.end is None:
            if p.first_start is None:
                p.first_start = p.arrival
                p.response = 0
            p.end = p.first_start + p.service
            p.finalize(p.end)
        if p.end > last_completion: last_completion = p.end
    segments = {sid + 1: [] for sid in range(servers_count)}
    for p in patients:
        for seg in p.segments:
            sid, st, en = seg[0], seg[1], seg[2] if seg[2] is not None else seg[1]
            segments[sid].append((p.id, int(st), int(en)))
    for sid in segments: segments[sid].sort(key=lambda s: s[1])
    server_busy_raw = {sid: sum(en - st for _, st, en in segments[sid]) for sid in segments}
    last_completion = max(1, last_completion)
    util_map = {sid: server_busy_raw.get(sid, 0) / last_completion for sid in range(1, servers_count + 1)}
    total_busy = sum(server_busy_raw.values())
    if total_busy > 0:
        util_share_map = {sid: server_busy_raw.get(sid, 0) / total_busy for sid in range(1, servers_count + 1)}
    else:
        util_share_map = {sid: 1.0 / max(1, servers_count) for sid in range(1, servers_count + 1)}
    avg_util = sum(util_map.values()) / max(1, len(util_map))
    return {'patients': patients, 'segments': segments, 'util_map': util_map, 'util_share_map': util_share_map, 'avg_util': avg_util, 'T': max(1, last_completion), 'inter_arr': inter_arr, 'arrivals': arrivals, 'services': services, 'timeline': timeline, 'queue': queue_lengths, 'arrival_dist': 'Exponential', 'service_dist': dist_type}

def simulate_nonpreemptive_fcfs(mean_arrival, mean_service, servers_count=1, dist_type="normal", a=None, b=None):
    cp, cp_lookup, avg_times, inter_arr, arrivals = generate_arrivals_by_cp(mean_arrival)
    n = len(arrivals)
    services = generate_service_times(n, mean_service, dist_type, a=a, b=b)
    patients = [Patient(i + 1, arrivals[i], services[i], priority=None) for i in range(n)]
    servers = [{'p': None, 'end': None} for _ in range(servers_count)]
    waiting = []
    arrival_idx = 0
    timeline = []
    queue_lengths = []
    util_over_time = []
    def next_arrival_time(): return patients[arrival_idx].arrival if arrival_idx < n else math.inf
    def next_completion_time():
        times = [s['end'] for s in servers if s['p'] is not None]
        return min(times) if times else math.inf
    while True:
        ta = next_arrival_time()
        tc = next_completion_time()
        if ta == tc == math.inf:
            break
        if ta <= tc:
            t = ta
            arrivals_at_t = []
            while arrival_idx < n and patients[arrival_idx].arrival == t:
                arrivals_at_t.append(patients[arrival_idx])
                arrival_idx += 1
            for newp in arrivals_at_t:
                free_sid = next((sid for sid, s in enumerate(servers) if s['p'] is None), None)
                if free_sid is not None:
                    newp.start_on(free_sid + 1, t)
                    servers[free_sid]['p'] = newp
                    servers[free_sid]['end'] = t + newp.remaining
                else:
                    waiting.append(newp)
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pick = waiting.pop(0)
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        else:
            t = tc
            for sid, s in enumerate(servers):
                if s['p'] is not None and s['end'] == t:
                    p = s['p']
                    p.stop_at(t)
                    seg_start = p.segments[-1][1]
                    consumed = int(t) - int(seg_start)
                    p.remaining = max(0, p.remaining - consumed)
                    p.finalize(t)
                    servers[sid] = {'p': None, 'end': None}
            assigned = True
            while assigned:
                assigned = False
                for sid, s in enumerate(servers):
                    if s['p'] is None and waiting:
                        pick = waiting.pop(0)
                        pick.start_on(sid + 1, t)
                        servers[sid]['p'] = pick
                        servers[sid]['end'] = t + pick.remaining
                        assigned = True
        busy_count = sum(1 for s in servers if s['p'] is not None)
        timeline.append(t)
        queue_lengths.append(len(waiting))
        util_over_time.append(busy_count / servers_count if servers_count > 0 else 0)
    last_completion = 0
    for p in patients:
        if p.end is None:
            if p.first_start is None:
                p.first_start = p.arrival
                p.response = 0
            p.end = p.first_start + p.service
            p.finalize(p.end)
        if p.end > last_completion: last_completion = p.end
    segments = {sid + 1: [] for sid in range(servers_count)}
    for p in patients:
        for seg in p.segments:
            sid, st, en = seg[0], seg[1], seg[2] if seg[2] is not None else seg[1]
            segments[sid].append((p.id, int(st), int(en)))
    for sid in segments: segments[sid].sort(key=lambda s: s[1])
    server_busy_raw = {sid: sum(en - st for _, st, en in segments[sid]) for sid in segments}
    last_completion = max(1, last_completion)
    util_map = {sid: server_busy_raw.get(sid, 0) / last_completion for sid in range(1, servers_count + 1)}
    total_busy = sum(server_busy_raw.values())
    if total_busy > 0:
        util_share_map = {sid: server_busy_raw.get(sid, 0) / total_busy for sid in range(1, servers_count + 1)}
    else:
        util_share_map = {sid: 1.0 / max(1, servers_count) for sid in range(1, servers_count + 1)}
    avg_util = sum(util_map.values()) / max(1, len(util_map))
    return {'patients': patients, 'segments': segments, 'util_map': util_map, 'util_share_map': util_share_map, 'avg_util': avg_util, 'T': max(1, last_completion), 'inter_arr': inter_arr, 'arrivals': arrivals, 'services': services, 'timeline': timeline, 'queue': queue_lengths, 'arrival_dist': 'Exponential', 'service_dist': dist_type}


class MedicareApp:
    def __init__(self, root):
        self.style = tb.Style("minty")
        self.root = self.style.master
        
        self.root.title("MEDICARE HEALTHCARE SYSTEM")
        # Maximized Window automatically for full-screen fit
        try:
            self.root.state('zoomed')
        except:
            self.root.geometry("1400x850")
            
        self.root.minsize(1100, 700)

        # Compact Header
        header = tb.Frame(self.root, bootstyle="success", padding=10)
        header.pack(fill=X)

        lbl_icon = ttk.Label(
            header,
            text="🏥",
            font=("Segoe UI Emoji", 24),
            background="#78C2AD",
            foreground="white"
        )
        lbl_icon.pack(side=LEFT, padx=(10, 5))

        lbl_title = ttk.Label(
            header,
            text="MEDICARE HEALTHCARE SYSTEM",
            font=("Helvetica", 18, "bold"),
            background="#78C2AD",
            foreground="white"
        )
        lbl_title.pack(side=LEFT)

        lbl_sub = ttk.Label(
            header,
            text="| Patient Queue Management Simulator",
            font=("Helvetica", 12),
            background="#78C2AD",
            foreground="#f1f1f1"
        )
        lbl_sub.pack(side=LEFT, padx=10, pady=(4, 0))

        self.main_pane = ttk.PanedWindow(self.root, orient=HORIZONTAL)
        self.main_pane.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # --- SCROLLABLE SIDEBAR SETUP ---
        sidebar_outer = ttk.Frame(self.main_pane, width=360)
        self.main_pane.add(sidebar_outer, weight=0)

        canvas_sidebar = tk.Canvas(sidebar_outer, borderwidth=0, highlightthickness=0)
        scrollbar_sidebar = ttk.Scrollbar(sidebar_outer, orient=VERTICAL, command=canvas_sidebar.yview)
        self.sidebar = ttk.Frame(canvas_sidebar, padding=10)

        self.sidebar.bind(
            "<Configure>",
            lambda e: canvas_sidebar.configure(scrollregion=canvas_sidebar.bbox("all"))
        )

        canvas_sidebar.create_window((0, 0), window=self.sidebar, anchor=NW)
        canvas_sidebar.configure(yscrollcommand=scrollbar_sidebar.set)

        canvas_sidebar.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar_sidebar.pack(side=RIGHT, fill=Y)

        # Mousewheel scroll support
        def _on_mousewheel(event):
            canvas_sidebar.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_sidebar.bind_all("<MouseWheel>", _on_mousewheel)

        # --- SIDEBAR CARDS ---
        card_flow = tb.LabelFrame(self.sidebar, text=" 🩺 Patient Flow Parameters ", padding=10, bootstyle="primary")
        card_flow.pack(fill=X, pady=(0, 10))
        self.create_entry_row(card_flow, "Arrival Rate (λ):", "1.0", "Patients/min").pack(fill=X, pady=3)
        self.e_lambda = self.last_entry
        self.dynamic_dist_frame = ttk.Frame(card_flow)
        self.dynamic_dist_frame.pack(fill=X, pady=3)
        self.label_arr_a = ttk.Label(self.dynamic_dist_frame, text="Arr Min (a):")
        self.e_arr_a = ttk.Entry(self.dynamic_dist_frame, width=5)
        self.e_arr_a.insert(0, "1")
        self.label_arr_b = ttk.Label(self.dynamic_dist_frame, text="Arr Max (b):")
        self.e_arr_b = ttk.Entry(self.dynamic_dist_frame, width=5)
        self.e_arr_b.insert(0, "5")
        self.dynamic_serv_frame = ttk.Frame(card_flow)
        self.dynamic_serv_frame.pack(fill=X, pady=3)
        self.label_mu = ttk.Label(self.dynamic_serv_frame, text="Treatment (μ):")
        self.e_mu = ttk.Entry(self.dynamic_serv_frame, width=8)
        self.e_mu.insert(0, "1.0")
        self.label_serv_a = ttk.Label(self.dynamic_serv_frame, text="Svc Min (a):")
        self.e_serv_a = ttk.Entry(self.dynamic_serv_frame, width=5)
        self.e_serv_a.insert(0, "1")
        self.label_serv_b = ttk.Label(self.dynamic_serv_frame, text="Svc Max (b):")
        self.e_serv_b = ttk.Entry(self.dynamic_serv_frame, width=5)
        self.e_serv_b.insert(0, "5")
        ttk.Label(card_flow, text="Arrival Dist:").pack(anchor="w", pady=(3,0))
        self.cb_arr_dist = ttk.Combobox(card_flow, values=["exponential", "normal", "uniform", "lognormal", "gamma"], state="readonly")
        self.cb_arr_dist.current(0)
        self.cb_arr_dist.pack(fill=X, pady=2)
        ttk.Label(card_flow, text="Service Dist:").pack(anchor="w", pady=(3,0))
        self.cb_serv_dist = ttk.Combobox(card_flow, values=["normal", "uniform", "lognormal", "gamma", "exponential"], state="readonly")
        self.cb_serv_dist.current(0)
        self.cb_serv_dist.pack(fill=X, pady=2)
        self.cb_serv_dist.bind("<<ComboboxSelected>>", self.on_serv_dist_change)
        
        card_res = tb.LabelFrame(self.sidebar, text=" 🏥 Hospital Resource Configuration ", padding=10, bootstyle="info")
        card_res.pack(fill=X, pady=10)
        self.create_entry_row(card_res, "Active Doctors/Clinics (s):", "2", "Units").pack(fill=X, pady=3)
        self.e_servers = self.last_entry
        ttk.Label(card_res, text="Queue Model:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 2))
        self.cb_model = ttk.Combobox(card_res, values=["M/M/s", "M/G/s", "G/G/s"], state="readonly")
        self.cb_model.current(0)
        self.cb_model.pack(fill=X)
        self.cb_model.bind("<<ComboboxSelected>>", self.on_model_change)
        
        card_prio = tb.LabelFrame(self.sidebar, text=" 🚨 Triage / Urgency Discipline ", padding=10, bootstyle="warning")
        card_prio.pack(fill=X, pady=10)
        self.priority_var = tk.BooleanVar(value=True)
        self.chk_priority = tb.Checkbutton(card_prio, text="Enable Priority (Preemptive)", variable=self.priority_var, bootstyle="round-toggle")
        self.chk_priority.pack(anchor="w", pady=(0, 5))
        r_pri = ttk.Frame(card_prio)
        r_pri.pack(fill=X)
        ttk.Label(r_pri, text="Urgency Levels:", font=("Arial", 9, "bold")).pack(side=LEFT)
        self.e_plow = ttk.Entry(r_pri, width=4)
        self.e_plow.insert(0, "1")
        self.e_plow.pack(side=LEFT, padx=3)
        ttk.Label(r_pri, text="to").pack(side=LEFT)
        self.e_phigh = ttk.Entry(r_pri, width=4)
        self.e_phigh.insert(0, "3")
        self.e_phigh.pack(side=LEFT, padx=3)
        
        ttk.Separator(self.sidebar).pack(fill=X, pady=10)
        self.btn_run = tb.Button(self.sidebar, text="▶ RUN SIMULATION", bootstyle="success", command=self.run_sim)
        self.btn_run.pack(fill=X, ipady=8, pady=4)
        self.btn_reset = tb.Button(self.sidebar, text="↺ RESET INPUTS", bootstyle="secondary-outline", command=self.reset_inputs)
        self.btn_reset.pack(fill=X, pady=4)
        
        # --- MAIN CONTENT AREA ---
        self.content_area = ttk.Frame(self.main_pane, padding=10)
        self.main_pane.add(self.content_area, weight=1)
        
        self.dash_frame = ttk.Frame(self.content_area)
        self.dash_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(self.dash_frame, text="Queuing Performance Indicators", font=("Helvetica", 14, "bold"), foreground="#7f8c8d").pack(anchor=tk.W, pady=(0,5))
        
        self.metrics_grid = ttk.Frame(self.dash_frame)
        self.metrics_grid.pack(fill=X)
        
        self.lbl_L = self.create_kpi_card(self.metrics_grid, "L (System)", "0.00", "info")
        self.lbl_Lq = self.create_kpi_card(self.metrics_grid, "Lq (Queue)", "0.00", "primary")
        self.lbl_W = self.create_kpi_card(self.metrics_grid, "Avg Turnaround (W)", "0.00", "success")
        self.lbl_Wq = self.create_kpi_card(self.metrics_grid, "Avg Wait (Wq)", "0.00", "warning")
        self.lbl_Rho = self.create_kpi_card(self.metrics_grid, "ρ (Utilization)", "0.00", "danger")

        self.nb = tb.Notebook(self.content_area, bootstyle="success")
        self.nb.pack(fill=BOTH, expand=YES, pady=(5,0))
        
        # TAB 1: LOGS
        self.tab_log = ttk.Frame(self.nb, padding=5)
        self.nb.add(self.tab_log, text=" 🧾 Patient Data Logs ")
        tree_scroll_y = ttk.Scrollbar(self.tab_log, orient=VERTICAL)
        tree_scroll_x = ttk.Scrollbar(self.tab_log, orient=HORIZONTAL)
        
        cols = ("no","inter","arrival","service","priority","start","end","wait","resp", "turn")
        
        self.tree = tb.Treeview(self.tab_log, columns=cols, show="headings", bootstyle="info", yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        tree_scroll_y.pack(side=RIGHT, fill=Y)
        tree_scroll_x.pack(side=BOTTOM, fill=X)
        self.tree.pack(fill=BOTH, expand=YES)
        
        col_conf = [
            ("no","Patient ID",70), 
            ("inter","Inter-Arr",70), 
            ("arrival","Arrive",70), 
            ("service","Treatment",80), 
            ("priority","Urgency",75), 
            ("start","Start",70), 
            ("end","Done",70), 
            ("wait","Wait (Wq)",85), 
            ("resp","Response",80),
            ("turn","Turnaround",95)
        ]
        for cid, txt, w in col_conf:
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor="center")
            
        # TAB 2: METRICS
        self.tab_perf = ttk.Frame(self.nb, padding=5)
        self.nb.add(self.tab_perf, text=" 📊 Doctor / Clinic Metrics ")
        self.tree_perf = tb.Treeview(self.tab_perf, columns=("server","avgt","avgw","avgr","util"), show="headings", bootstyle="secondary")
        perf_heads = [("server","Doctor/Clinic ID"),("avgt","Avg Treatment Time"),("avgw","Avg Queue Time"),("avgr","Avg Response"),("util","Utilization")]
        for col, head in perf_heads:
            self.tree_perf.heading(col, text=head)
            self.tree_perf.column(col, width=130, anchor="center")
        self.tree_perf.pack(fill=BOTH, expand=YES)
        
        # TAB 3: GANTT TIMELINE
        self.tab_timeline = ttk.Frame(self.nb, padding=5)
        self.nb.add(self.tab_timeline, text=" 📅 Treatment Gantt Timeline ")
        self.timeline_frame = ttk.Frame(self.tab_timeline)
        self.timeline_frame.pack(fill=BOTH, expand=YES)
        
        self.on_model_change()

    def create_entry_row(self, parent, label, default, unit):
        f = ttk.Frame(parent)
        ttk.Label(f, text=label, width=16, font=("Arial", 8, "bold")).pack(side=LEFT)
        e = ttk.Entry(f)
        e.insert(0, default)
        e.pack(side=LEFT, fill=X, expand=YES)
        ttk.Label(f, text=unit, font=("Arial", 8), foreground="gray").pack(side=RIGHT, padx=3)
        self.last_entry = e
        return f

    def create_kpi_card(self, parent, title, val, color):
        f = tb.Frame(parent, bootstyle=f"{color}-bg", padding=10)
        f.pack(side=LEFT, expand=YES, fill=X, padx=3)
        ttk.Label(f, text=title, font=("Arial", 9, "bold"), foreground="white", background=self.style.colors.get(color)).pack(anchor="w")
        lbl = ttk.Label(f, text=val, font=("Arial", 18, "bold"), foreground="white", background=self.style.colors.get(color))
        lbl.pack(anchor="w")
        return lbl

    def reset_inputs(self):
        self.e_lambda.delete(0, END)
        self.e_lambda.insert(0, "1.0")
        self.e_mu.delete(0, END)
        self.e_mu.insert(0, "1.0")
        self.e_arr_a.delete(0, END)
        self.e_arr_a.insert(0, "1")
        self.e_arr_b.delete(0, END)
        self.e_arr_b.insert(0, "5")
        self.e_serv_a.delete(0, END)
        self.e_serv_a.insert(0, "1")
        self.e_serv_b.delete(0, END)
        self.e_serv_b.insert(0, "5")
        self.cb_model.set("M/M/s")
        self.e_servers.delete(0, END)
        self.e_servers.insert(0, "2")
        self.priority_var.set(True)
        self.on_model_change()
        self.update_metric_labels(0,0,0,0,0)
        for i in self.tree.get_children(): self.tree.delete(i)
        for i in self.tree_perf.get_children(): self.tree_perf.delete(i)
        for w in self.timeline_frame.winfo_children(): w.destroy()

    def update_metric_labels(self, L, Lq, W, Wq, rho):
        self.lbl_L.config(text=f"{L:.2f} Pts")
        self.lbl_Lq.config(text=f"{Lq:.2f} Pts")
        self.lbl_W.config(text=f"{W:.2f} Min")
        self.lbl_Wq.config(text=f"{Wq:.2f} Min")
        self.lbl_Rho.config(text=f"{rho:.2f}")

    def on_serv_dist_change(self, event=None):
        dist = self.cb_serv_dist.get()
        if dist == "uniform":
            self.label_mu.grid_remove()
            self.e_mu.grid_remove()
            self.label_serv_a.grid(row=0, column=0)
            self.e_serv_a.grid(row=0, column=1)
            self.label_serv_b.grid(row=0, column=2)
            self.e_serv_b.grid(row=0, column=3)
        else:
            self.label_mu.grid(row=0, column=0, sticky="w")
            self.e_mu.grid(row=0, column=1, sticky="w")
            self.label_serv_a.grid_remove()
            self.e_serv_a.grid_remove()
            self.label_serv_b.grid_remove()
            self.e_serv_b.grid_remove()

    def on_model_change(self, event=None):
        model = self.cb_model.get()
        if model == "M/M/s":
            self.cb_arr_dist.set("exponential")
            self.cb_arr_dist.config(state="disabled")
            self.cb_serv_dist.set("exponential")
            self.cb_serv_dist.config(state="disabled")
            self.label_arr_a.grid_remove()
            self.e_arr_a.grid_remove()
            self.label_arr_b.grid_remove()
            self.e_arr_b.grid_remove()
            self.on_serv_dist_change()
        elif model == "M/G/s":
            self.cb_arr_dist.set("exponential")
            self.cb_arr_dist.config(state="disabled")
            self.cb_serv_dist.config(state="readonly")
            self.label_arr_a.grid_remove()
            self.e_arr_a.grid_remove()
            self.label_arr_b.grid_remove()
            self.e_arr_b.grid_remove()
            self.on_serv_dist_change()
        elif model == "G/G/s":
            self.cb_arr_dist.config(state="readonly")
            self.cb_serv_dist.config(state="readonly")
            self.on_serv_dist_change()
            if self.cb_arr_dist.get() == "uniform":
                self.label_arr_a.grid(row=0, column=0)
                self.e_arr_a.grid(row=0, column=1)
                self.label_arr_b.grid(row=0, column=2)
                self.e_arr_b.grid(row=0, column=3)
            else:
                self.label_arr_a.grid_remove()
                self.e_arr_a.grid_remove()
                self.label_arr_b.grid_remove()
                self.e_arr_b.grid_remove()

    def run_sim(self):
        try:
            model = self.cb_model.get()
            lam = float(self.e_lambda.get())
            servers = int(self.e_servers.get())
            pl = int(self.e_plow.get())
            ph = int(self.e_phigh.get())
            use_p = bool(self.priority_var.get())
            if model == "M/M/s":
                if use_p:
                    res = simulate_preemptive_v5(lam, float(self.e_mu.get()), servers, (pl, ph), "exponential")
                else:
                    res = simulate_nonpreemptive_fcfs(lam, float(self.e_mu.get()), servers, "exponential")
            elif model == "M/G/s":
                dist = self.cb_serv_dist.get()
                mu = float(self.e_mu.get()) if dist != "uniform" else None
                a = float(self.e_serv_a.get()) if dist == "uniform" else None
                b = float(self.e_serv_b.get()) if dist == "uniform" else None
                mu = (a+b)/2.0 if dist == "uniform" else mu
                if use_p:
                    res = simulate_preemptive_v5(lam, mu, servers, (pl, ph), dist, a, b)
                else:
                    res = simulate_nonpreemptive_fcfs(lam, mu, servers, dist, a, b)
            elif model == "G/G/s":
                arr_dist = self.cb_arr_dist.get()
                serv_dist = self.cb_serv_dist.get()
                mu = float(self.e_mu.get()) if serv_dist != "uniform" else (float(self.e_serv_a.get())+float(self.e_serv_b.get()))/2
                if use_p:
                    res = simulate_ggs_preemptive(lam, mu, servers, (pl, ph), arr_dist, serv_dist)
                else:
                    res = simulate_ggs_nonpreemptive(lam, mu, servers, arr_dist, serv_dist)
        except:
            messagebox.showerror("Input Error", "Check inputs")
            return
        self.update_tables(res, use_p)
        self.update_giant_timeline(res, use_p, model)
        pats = res['patients']
        if pats:
            W = mean([p.turnaround for p in pats])
            Wq = mean([p.wait for p in pats])
            total_sim_time = res['T']
            if total_sim_time > 0:
                L = sum([p.turnaround for p in pats]) / total_sim_time
                Lq = sum([p.wait for p in pats]) / total_sim_time
            else:
                L = 0
                Lq = 0

            rho = 0.0
            try:
                if lam > 0 and servers > 0:
                    if model == "M/M/s":
                        mu_r = float(self.e_mu.get())
                    else:
                        serv_dist = self.cb_serv_dist.get()
                        if serv_dist == "uniform":
                            a_r = float(self.e_serv_a.get())
                            b_r = float(self.e_serv_b.get())
                            mu_r = (a_r + b_r) / 2.0
                        else:
                            mu_r = float(self.e_mu.get())
                    if mu_r > 0:
                        rho = lam / (servers * mu_r)
                        if rho > 1.0:
                            rho = 1.0
            except:
                rho = 0.0

            self.update_metric_labels(L, Lq, W, Wq, rho)
        self.nb.select(0)

    def update_tables(self, res, use_p):
        for i in self.tree.get_children(): self.tree.delete(i)
        for i, p in enumerate(res['patients']):
            pri_txt = p.priority if (use_p and p.priority is not None) else "Std"
            vals = (f"P{p.id}", f"{res['inter_arr'][i]:.2f}", res['arrivals'][i], res['services'][i], pri_txt, p.first_start, p.end, p.wait, p.response, p.turnaround)
            self.tree.insert("", "end", values=vals)
        for i in self.tree_perf.get_children(): self.tree_perf.delete(i)
        all_servers = sorted(res['util_map'].keys())
        for sid in all_servers:
            segs = res['segments'].get(sid, [])
            pids = [pid for pid, _, _ in segs]
            pats = [p for p in res['patients'] if p.id in pids]
            if pats:
                avgt = mean([p.turnaround for p in pats])
                avgw = mean([p.wait for p in pats])
                avgr = mean([p.response for p in pats])
            else:
                avgt = 0.0
                avgw = 0.0
                avgr = 0.0
            u = res.get('util_share_map', res.get('util_map', {})).get(sid, 0.0)
            self.tree_perf.insert("", "end", values=(f"Doctor {sid}", f"{avgt:.2f}", f"{avgw:.2f}", f"{avgr:.2f}", f"{u:.2%}"))

    def update_giant_timeline(self, res, use_p, model):
        for w in self.timeline_frame.winfo_children(): w.destroy()
        plt.style.use('seaborn-v0_8-whitegrid')
        fig = plt.figure(figsize=(10, 5), dpi=100)
        ax = fig.add_subplot(111)
        pri_colors = {1: "#E74C3C", 2: "#F39C12", 3: "#18BC9C"}
        cycle_colors = ["#2C3E50", "#78C2AD", "#3498DB", "#95A5A6"]
        y = 0
        for sid in sorted(res['segments'].keys()):
            for pid, st, en in res['segments'][sid]:
                p = next((pp for pp in res['patients'] if pp.id == pid), None)
                color = pri_colors.get(p.priority, cycle_colors[0]) if use_p else cycle_colors[(pid-1)%len(cycle_colors)]
                ax.barh(y, max(0.001, en-st), left=st, height=0.6, color=color, edgecolor='white', alpha=0.9)
                mid_point = st + (en - st) / 2
                ax.text(mid_point, y, f"P{pid}", ha='center', va='center', fontsize=8, fontweight='bold', color='white')
            ax.text(-0.5, y, f"Doctor {sid}", va='center', ha='right', fontsize=10, fontweight='bold', color="#2c3e50")
            y += 1
        total_c = len(res['patients'])
        ax.set_xlabel('Timeline (Minutes)', fontsize=10)
        ax.set_title(f'Gantt Doctor Schedule [{model}] - Total Patients: {total_c}', fontsize=12, pad=10, color="#2c3e50")
        ax.set_yticks([])
        ax.grid(axis='x', linestyle='--', alpha=0.6)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        handles = []
        labels = []
        if use_p:
            for pri, col in pri_colors.items():
                handles.append(plt.Rectangle((0,0),1,1, color=col))
                labels.append(f"Urgency Lvl {pri}")
        else:
            handles.append(plt.Rectangle((0,0),1,1, color=cycle_colors[0]))
            labels.append("Patient")
        ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False, fontsize=9)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.timeline_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES)

if __name__ == "__main__":
    root = tb.Window(themename="minty")
    app = MedicareApp(root)
    root.mainloop()