from os.path import join
from numpy.core.fromnumeric import size
import torch
import torch.nn.functional as F
from tqdm import tqdm
from utils.config import opt
from model.sinkhorn_distance import SinkhornDistance

def substructure_matching_distance(targets_src, boxes_t, label_num):
    # 获取到结点数量、结点类别以及结点bounding box
    n = len(targets_src.fields['labels'])
    if n != label_num:
        return torch.tensor(0,device=opt.device,dtype=float)
    label_s = targets_src.fields['labels']
    box_s = targets_src.box
    label_t = boxes_t.fields['labels']
    box_t = boxes_t.box
    # 处理source的排序问题
    sorted_indices = torch.argsort(label_s)
    label_s = label_s[sorted_indices]
    box_s = box_s[sorted_indices]
    # 获取score最高的target的结点
    arr = []
    for i in range(label_t.min(),label_t.max()+1):
        l = torch.where(label_t == i)
        if l is not None and l[0].shape[0] != 0:
            arr.append(l[0][0].item())
            if i == 9 and l[0].shape[0] > 1:
                arr.append(l[0][1].item())

    label_t = label_t[arr]
    box_t = box_t[arr]

    if label_t.shape[0] != label_num:
        return torch.tensor(0,device=opt.device,dtype=float)

    # 得到中间点
    midpoint_s = []
    midpoint_t = []
    for i in range(n):
        midpoint_s.append([(box_s[i][0]+box_s[i][2])/2, (box_s[i][1]+box_s[i][3])/2])
        midpoint_t.append([(box_t[i][0]+box_t[i][2])/2, (box_t[i][1]+box_t[i][3])/2])
    
    midpoint_s = torch.tensor(midpoint_s)
    midpoint_t = torch.tensor(midpoint_t)
    # 获得邻接矩阵
    adj_s = torch.cdist(midpoint_s, midpoint_s).to(device=opt.device)
    adj_t = torch.cdist(midpoint_t, midpoint_t).to(device=opt.device)
    # 计算距离loss
    if len(arr) == 9:
        dis_s = adj_s[6][8].to(device=opt.device)
        dis_t = adj_t[6][8].to(device=opt.device)
        
    elif len(arr) == label_num:
        dis_s = ((adj_s[6][8]+adj_s[6][9])/2).to(device=opt.device)
        dis_t = ((adj_t[6][8]+adj_t[6][9])/2).to(device=opt.device)
    else:
        return torch.tensor(0,device=opt.device,dtype=float)
    
    dis_rate_s = dis_s/opt.match_key_distance
    dis_rate_t = dis_t/opt.match_key_distance
    adj_s = adj_s * dis_rate_s
    adj_t = adj_t * dis_rate_t
    distance_diff_abs = torch.sum(torch.abs(adj_s - adj_t)).to(device=opt.device)
    
    return distance_diff_abs * 0.01


def substructure_matching_sinkhorn(targets_src, boxes_t, label_num):
    # 获取到结点数量、结点类别以及结点bounding box
    n = len(targets_src.fields['labels'])
    if n != label_num:
        return torch.tensor(0,device=opt.device,dtype=float)
    label_s = targets_src.fields['labels']
    box_s = targets_src.box
    label_t = boxes_t.fields['labels']
    box_t = boxes_t.box
    # 处理source的排序问题
    sorted_indices = torch.argsort(label_s)
    label_s = label_s[sorted_indices]
    box_s = box_s[sorted_indices]
    # 获取score最高的target的结点
    arr = []
    for i in range(label_t.min(),label_t.max()+1):
        l = torch.where(label_t == i)
        if l is not None and l[0].shape[0] != 0:
            arr.append(l[0][0].item())

    label_t = label_t[arr]
    box_t = box_t[arr]

    if label_t.shape[0] != label_num:
        return torch.tensor(0,device=opt.device,dtype=float)

    # 得到中间点
    midpoint_s = []
    midpoint_t = []
    for i in range(n):
        midpoint_s.append([(box_s[i][0]+box_s[i][2])/2, (box_s[i][1]+box_s[i][3])/2])
        midpoint_t.append([(box_t[i][0]+box_t[i][2])/2, (box_t[i][1]+box_t[i][3])/2])
    
    coordinates_s = torch.tensor(midpoint_s)
    coordinates_t = torch.tensor(midpoint_t)
    # 获得角度邻接矩阵
    adjacency_matrix_s = torch.zeros(label_num, label_num).to(device=opt.device)
    adjacency_matrix_t = torch.zeros(label_num, label_num).to(device=opt.device)

    # 填充邻接矩阵，存储角度大小
    for i in range(label_num):
        for j in range(label_num):
            if i != j:
                angle_s = calculate_angle(coordinates_s[i], coordinates_s[j])
                angle_t = calculate_angle(coordinates_t[i], coordinates_t[j])
                adjacency_matrix_s[i][j] = angle_s
                adjacency_matrix_t[i][j] = angle_t
    
    
    sinkhornDistance = SinkhornDistance(0.001, 120)
    loss, _, _ = sinkhornDistance(adjacency_matrix_s, adjacency_matrix_t)
    
    return loss[0]


# 计算点之间的角度（弧度）
def calculate_angle(point1, point2):
    delta_x = point2[0] - point1[0]
    delta_y = point2[1] - point1[1]
    angle = torch.atan2(delta_y, delta_x)
    return angle