import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.nn.functional as F
from torch.nn import Parameter
import math

def myphi(x,m):
    x = x * m
    return 1-x**2/math.factorial(2)+x**4/math.factorial(4)-x**6/math.factorial(6) + \
            x**8/math.factorial(8) - x**9/math.factorial(9)

class AngleLinear(nn.Module):
    def __init__(self, in_features, out_features, m = 4, phiflag=True):
        super(AngleLinear, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = Parameter(torch.Tensor(in_features,out_features))
        self.weight.data.uniform_(-1, 1).renorm_(2,1,1e-5).mul_(1e5)
        self.phiflag = phiflag
        self.m = m
        self.mlambda = [
            lambda x: x**0,
            lambda x: x**1,
            lambda x: 2*x**2-1,
            lambda x: 4*x**3-3*x,
            lambda x: 8*x**4-8*x**2+1,
            lambda x: 16*x**5-20*x**3+5*x
        ]

    def forward(self, input):
        x = input   # size=(B,F)    F is feature len
        w = self.weight # size=(F,Classnum) F=in_features Classnum=out_features

        ww = w.renorm(2,1,1e-5).mul(1e5)
        xlen = x.pow(2).sum(1).pow(0.5) # size=B
        wlen = ww.pow(2).sum(0).pow(0.5) # size=Classnum

        cos_theta = x.mm(ww) # size=(B,Classnum)
        cos_theta = cos_theta / xlen.view(-1,1) / wlen.view(1,-1)
        cos_theta = cos_theta.clamp(-1,1)

        if self.phiflag:
            cos_m_theta = self.mlambda[self.m](cos_theta)
            theta = Variable(cos_theta.data.acos())
            k = (self.m*theta/3.14159265).floor()
            n_one = k*0.0 - 1
            phi_theta = (n_one**k) * cos_m_theta - 2*k
        else:
            theta = cos_theta.acos()
            phi_theta = myphi(theta,self.m)
            phi_theta = phi_theta.clamp(-1*self.m,1)

        cos_theta = cos_theta * xlen.view(-1,1)
        phi_theta = phi_theta * xlen.view(-1,1)
        output = (cos_theta,phi_theta)
        return output # size=(B,Classnum,2)


class AngleLoss(nn.Module):
    def __init__(self, gamma=0):
        super(AngleLoss, self).__init__()
        self.gamma   = gamma
        self.it = 0
        self.LambdaMin = 5.0
        self.LambdaMax = 1500.0
        self.lamb = 1500.0

    def forward(self, input, target):
        self.it += 1
        cos_theta,phi_theta = input
        target = target.view(-1,1) #size=(B,1)

        index = cos_theta.data * 0.0 #size=(B,Classnum)
        index.scatter_(1,target.data.view(-1,1),1)
        index = index.byte()
        index = Variable(index)

        self.lamb = max(self.LambdaMin,self.LambdaMax/(1+0.1*self.it ))
        output = cos_theta * 1.0 #size=(B,Classnum)
        output[index] -= cos_theta[index]*(1.0+0)/(1+self.lamb)
        output[index] += phi_theta[index]*(1.0+0)/(1+self.lamb)

        logpt = F.log_softmax(output)
        logpt = logpt.gather(1,target)
        logpt = logpt.view(-1)
        pt = Variable(logpt.data.exp())

        loss = -1 * (1-pt)**self.gamma * logpt
        loss = loss.mean()

        return loss


class sphere20a(nn.Module):
    def __init__(self,classnum=2,feature=False):
        super(sphere20a, self).__init__()
        self.classnum = classnum
        self.feature = feature
        #input = B*3*112*96
        self.conv1_1 = nn.Conv2d(3,64,3,2,1) #=>B*64*56*48
        self.relu1_1 = nn.PReLU(64)
        self.conv1_2 = nn.Conv2d(64,64,3,1,1)
        self.relu1_2 = nn.PReLU(64)
        self.conv1_3 = nn.Conv2d(64,64,3,1,1)
        self.relu1_3 = nn.PReLU(64)

        self.conv2_1 = nn.Conv2d(64,128,3,2,1) #=>B*128*28*24
        self.relu2_1 = nn.PReLU(128)
        self.conv2_2 = nn.Conv2d(128,128,3,1,1)
        self.relu2_2 = nn.PReLU(128)
        self.conv2_3 = nn.Conv2d(128,128,3,1,1)
        self.relu2_3 = nn.PReLU(128)

        self.conv2_4 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_4 = nn.PReLU(128)
        self.conv2_5 = nn.Conv2d(128,128,3,1,1)
        self.relu2_5 = nn.PReLU(128)


        self.conv3_1 = nn.Conv2d(128,256,3,2,1) #=>B*256*14*12
        self.relu3_1 = nn.PReLU(256)
        self.conv3_2 = nn.Conv2d(256,256,3,1,1)
        self.relu3_2 = nn.PReLU(256)
        self.conv3_3 = nn.Conv2d(256,256,3,1,1)
        self.relu3_3 = nn.PReLU(256)

        self.conv3_4 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_4 = nn.PReLU(256)
        self.conv3_5 = nn.Conv2d(256,256,3,1,1)
        self.relu3_5 = nn.PReLU(256)

        self.conv3_6 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_6 = nn.PReLU(256)
        self.conv3_7 = nn.Conv2d(256,256,3,1,1)
        self.relu3_7 = nn.PReLU(256)

        self.conv3_8 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_8 = nn.PReLU(256)
        self.conv3_9 = nn.Conv2d(256,256,3,1,1)
        self.relu3_9 = nn.PReLU(256)

        self.conv4_1 = nn.Conv2d(256,512,3,2,1) #=>B*512*7*6
        self.relu4_1 = nn.PReLU(512)
        self.conv4_2 = nn.Conv2d(512,512,3,1,1)
        self.relu4_2 = nn.PReLU(512)
        self.conv4_3 = nn.Conv2d(512,512,3,1,1)
        self.relu4_3 = nn.PReLU(512)

        self.fc5 = nn.Linear(512*13*13,512)
        self.fc6 = AngleLinear(512,self.classnum)


    def forward(self, x):
        x = self.relu1_1(self.conv1_1(x))
        x = x + self.relu1_3(self.conv1_3(self.relu1_2(self.conv1_2(x))))

        x = self.relu2_1(self.conv2_1(x))
        x = x + self.relu2_3(self.conv2_3(self.relu2_2(self.conv2_2(x))))
        x = x + self.relu2_5(self.conv2_5(self.relu2_4(self.conv2_4(x))))

        x = self.relu3_1(self.conv3_1(x))
        x = x + self.relu3_3(self.conv3_3(self.relu3_2(self.conv3_2(x))))
        x = x + self.relu3_5(self.conv3_5(self.relu3_4(self.conv3_4(x))))
        x = x + self.relu3_7(self.conv3_7(self.relu3_6(self.conv3_6(x))))
        x = x + self.relu3_9(self.conv3_9(self.relu3_8(self.conv3_8(x))))

        x = self.relu4_1(self.conv4_1(x))
        x = x + self.relu4_3(self.conv4_3(self.relu4_2(self.conv4_2(x))))
        x = x.view(x.size(0),-1)
        x = self.fc5(x)
        if self.feature: return x

        x = self.fc6(x)
        return x

class sphere64a(nn.Module):
    def __init__(self,classnum=2,feature=False):
        super(sphere64a, self).__init__()
        self.classnum = classnum
        self.feature = feature
        #input = B*3*112*96
        self.conv1_1 = nn.Conv2d(3,64,3,2,1) #=>B*64*56*48
        self.relu1_1 = nn.PReLU(64)
        self.conv1_2 = nn.Conv2d(64,64,3,1,1)
        self.relu1_2 = nn.PReLU(64)
        self.conv1_3 = nn.Conv2d(64,64,3,1,1)
        self.relu1_3 = nn.PReLU(64)

        self.conv1_4 = nn.Conv2d(64,64,3,1,1)
        self.relu1_4 = nn.PReLU(64)
        self.conv1_5 = nn.Conv2d(64,64,3,1,1)
        self.relu1_5 = nn.PReLU(64)

        self.conv1_6 = nn.Conv2d(64,64,3,1,1)
        self.relu1_6 = nn.PReLU(64)
        self.conv1_7 = nn.Conv2d(64,64,3,1,1)
        self.relu1_7 = nn.PReLU(64)


        self.conv2_1 = nn.Conv2d(64,128,3,2,1) #=>B*128*28*24
        self.relu2_1 = nn.PReLU(128)
        self.conv2_2 = nn.Conv2d(128,128,3,1,1)
        self.relu2_2 = nn.PReLU(128)
        self.conv2_3 = nn.Conv2d(128,128,3,1,1)
        self.relu2_3 = nn.PReLU(128)

        self.conv2_4 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_4 = nn.PReLU(128)
        self.conv2_5 = nn.Conv2d(128,128,3,1,1)
        self.relu2_5 = nn.PReLU(128)

        self.conv2_6 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_6 = nn.PReLU(128)
        self.conv2_7 = nn.Conv2d(128,128,3,1,1)
        self.relu2_7 = nn.PReLU(128)

        self.conv2_8 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_8 = nn.PReLU(128)
        self.conv2_9 = nn.Conv2d(128,128,3,1,1)
        self.relu2_9 = nn.PReLU(128)

        self.conv2_10 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_10 = nn.PReLU(128)
        self.conv2_11 = nn.Conv2d(128,128,3,1,1)
        self.relu2_11 = nn.PReLU(128)

        self.conv2_12 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_12 = nn.PReLU(128)
        self.conv2_13 = nn.Conv2d(128,128,3,1,1)
        self.relu2_13 = nn.PReLU(128)

        self.conv2_14 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_14 = nn.PReLU(128)
        self.conv2_15 = nn.Conv2d(128,128,3,1,1)
        self.relu2_15 = nn.PReLU(128)

        self.conv2_16 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_16 = nn.PReLU(128)
        self.conv2_17 = nn.Conv2d(128,128,3,1,1)
        self.relu2_17 = nn.PReLU(128)



        self.conv3_1 = nn.Conv2d(128,256,3,2,1) #=>B*256*14*12
        self.relu3_1 = nn.PReLU(256)
        self.conv3_2 = nn.Conv2d(256,256,3,1,1)
        self.relu3_2 = nn.PReLU(256)
        self.conv3_3 = nn.Conv2d(256,256,3,1,1)
        self.relu3_3 = nn.PReLU(256)

        self.conv3_4 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_4 = nn.PReLU(256)
        self.conv3_5 = nn.Conv2d(256,256,3,1,1)
        self.relu3_5 = nn.PReLU(256)

        self.conv3_6 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_6 = nn.PReLU(256)
        self.conv3_7 = nn.Conv2d(256,256,3,1,1)
        self.relu3_7 = nn.PReLU(256)

        self.conv3_8 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_8 = nn.PReLU(256)
        self.conv3_9 = nn.Conv2d(256,256,3,1,1)
        self.relu3_9 = nn.PReLU(256)

        self.conv3_10 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_10 = nn.PReLU(256)
        self.conv3_11 = nn.Conv2d(256,256,3,1,1)
        self.relu3_11 = nn.PReLU(256)

        self.conv3_12 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_12 = nn.PReLU(256)
        self.conv3_13 = nn.Conv2d(256,256,3,1,1)
        self.relu3_13 = nn.PReLU(256)

        self.conv3_14 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_14 = nn.PReLU(256)
        self.conv3_15 = nn.Conv2d(256,256,3,1,1)
        self.relu3_15 = nn.PReLU(256)

        self.conv3_16 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_16 = nn.PReLU(256)
        self.conv3_17 = nn.Conv2d(256,256,3,1,1)
        self.relu3_17 = nn.PReLU(256)

        self.conv3_18 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_18 = nn.PReLU(256)
        self.conv3_19 = nn.Conv2d(256,256,3,1,1)
        self.relu3_19 = nn.PReLU(256)

        self.conv3_20 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_20 = nn.PReLU(256)
        self.conv3_21 = nn.Conv2d(256,256,3,1,1)
        self.relu3_21 = nn.PReLU(256)

        self.conv3_22 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_22 = nn.PReLU(256)
        self.conv3_23 = nn.Conv2d(256,256,3,1,1)
        self.relu3_23 = nn.PReLU(256)

        self.conv3_24 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_24 = nn.PReLU(256)
        self.conv3_25 = nn.Conv2d(256,256,3,1,1)
        self.relu3_25 = nn.PReLU(256)

        self.conv3_26 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_26 = nn.PReLU(256)
        self.conv3_27 = nn.Conv2d(256,256,3,1,1)
        self.relu3_27 = nn.PReLU(256)

        self.conv3_28 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_28 = nn.PReLU(256)
        self.conv3_29 = nn.Conv2d(256,256,3,1,1)
        self.relu3_29 = nn.PReLU(256)

        self.conv3_30 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_30 = nn.PReLU(256)
        self.conv3_31 = nn.Conv2d(256,256,3,1,1)
        self.relu3_31 = nn.PReLU(256)

        self.conv3_32 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_32 = nn.PReLU(256)
        self.conv3_33 = nn.Conv2d(256,256,3,1,1)
        self.relu3_33 = nn.PReLU(256)



        self.conv4_1 = nn.Conv2d(256,512,3,2,1) #=>B*512*7*6
        self.relu4_1 = nn.PReLU(512)
        self.conv4_2 = nn.Conv2d(512,512,3,1,1)
        self.relu4_2 = nn.PReLU(512)
        self.conv4_3 = nn.Conv2d(512,512,3,1,1)
        self.relu4_3 = nn.PReLU(512)

        self.conv4_4 = nn.Conv2d(512,512,3,1,1)
        self.relu4_4 = nn.PReLU(512)
        self.conv4_5 = nn.Conv2d(512,512,3,1,1)
        self.relu4_5 = nn.PReLU(512)

        self.conv4_6 = nn.Conv2d(512,512,3,1,1)
        self.relu4_6 = nn.PReLU(512)
        self.conv4_7 = nn.Conv2d(512,512,3,1,1)
        self.relu4_7 = nn.PReLU(512)


        self.fc5 = nn.Linear(512*13*13,512)
        self.fc6 = AngleLinear(512,self.classnum)


    def forward(self, x):
        x = self.relu1_1(self.conv1_1(x))
        x = x + self.relu1_3(self.conv1_3(self.relu1_2(self.conv1_2(x))))
        x = x + self.relu1_5(self.conv1_5(self.relu1_4(self.conv1_4(x))))
        x = x + self.relu1_7(self.conv1_7(self.relu1_6(self.conv1_6(x))))


        x = self.relu2_1(self.conv2_1(x))
        x = x + self.relu2_3(self.conv2_3(self.relu2_2(self.conv2_2(x))))
        x = x + self.relu2_5(self.conv2_5(self.relu2_4(self.conv2_4(x))))
        x = x + self.relu2_7(self.conv2_7(self.relu2_6(self.conv2_6(x))))
        x = x + self.relu2_9(self.conv2_9(self.relu2_8(self.conv2_8(x))))
        x = x + self.relu2_11(self.conv2_11(self.relu2_10(self.conv2_10(x))))
        x = x + self.relu2_13(self.conv2_13(self.relu2_12(self.conv2_12(x))))
        x = x + self.relu2_15(self.conv2_15(self.relu2_14(self.conv2_14(x))))
        x = x + self.relu2_17(self.conv2_17(self.relu2_16(self.conv2_16(x))))



        x = self.relu3_1(self.conv3_1(x))
        x = x + self.relu3_3(self.conv3_3(self.relu3_2(self.conv3_2(x))))
        x = x + self.relu3_5(self.conv3_5(self.relu3_4(self.conv3_4(x))))
        x = x + self.relu3_7(self.conv3_7(self.relu3_6(self.conv3_6(x))))
        x = x + self.relu3_9(self.conv3_9(self.relu3_8(self.conv3_8(x))))
        x = x + self.relu3_11(self.conv3_11(self.relu3_10(self.conv3_10(x))))
        x = x + self.relu3_13(self.conv3_13(self.relu3_12(self.conv3_12(x))))
        x = x + self.relu3_15(self.conv3_15(self.relu3_14(self.conv3_14(x))))
        x = x + self.relu3_17(self.conv3_17(self.relu3_16(self.conv3_16(x))))
        x = x + self.relu3_19(self.conv3_19(self.relu3_18(self.conv3_18(x))))
        x = x + self.relu3_21(self.conv3_21(self.relu3_20(self.conv3_20(x))))
        x = x + self.relu3_23(self.conv3_23(self.relu3_22(self.conv3_22(x))))
        x = x + self.relu3_25(self.conv3_25(self.relu3_24(self.conv3_24(x))))
        x = x + self.relu3_27(self.conv3_27(self.relu3_26(self.conv3_26(x))))
        x = x + self.relu3_29(self.conv3_29(self.relu3_28(self.conv3_28(x))))
        x = x + self.relu3_31(self.conv3_31(self.relu3_30(self.conv3_30(x))))
        x = x + self.relu3_33(self.conv3_33(self.relu3_32(self.conv3_32(x))))


        x = self.relu4_1(self.conv4_1(x))
        x = x + self.relu4_3(self.conv4_3(self.relu4_2(self.conv4_2(x))))
        x = x + self.relu4_5(self.conv4_5(self.relu4_4(self.conv4_4(x))))
        x = x + self.relu4_7(self.conv4_7(self.relu4_6(self.conv4_6(x))))
        x = x.view(x.size(0),-1)
        x = self.fc5(x)
        if self.feature: return x

        x = self.fc6(x)
        return x
