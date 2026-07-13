class Solution:
    #最小覆盖子串
    def minWindow(self, s: str, t: str) -> str:
        need = defaultdict(int)
        window = defaultdict(int)

        for i in t:
            need[i] += 1
        
        left = right = 0
        start = 0
        min_len = float("inf")
        vaild = 0

        for right in range(len(s)):
            if s[right] in need:
                window[s[right]]+=1
                if window[s[right]] == need[s[right]]:
                    vaild +=1
            while vaild == len(need):
                if right-left+1<min_len:

                    start = left

                    min_len = right-left+1
                if s[left] in need:
                    if window[s[left]] == need[s[left]]:
                        vaild -=1
                    window[s[left]] -= 1
                left += 1

        return "" if min_len == float('inf') else s[start:start+min_len]
        
class Solution:
    def coinChange(self, coins: List[int], amount: int) -> int:
        dp = [float("inf")]*(amount+1)
        dp[0] = 0

        for i in range(1,amount+1):
            for coin in coins:
                if i>=coin:
                    dp[i] = min(dp[i],dp[i-coin]+1)

        return -1 if  dp[amount] == float("inf") else dp[amount]
    
class Solution:
    def nextPermutation(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        #从末尾开始找，先找到左边比右边小的，然后再找比这个数字大的
        n = len(nums)
        i = n-2
        
        while i>=0 and nums[i]>=nums[i+1]:
            i -=1
        if i >=0:
            j = n-1
            while j>=0 and nums[j]<=nums[i]:
                j -=1
        
            nums[i],nums[j] = nums[j],nums[i]

        left = i+1
        right = n-1
        while left<right:
            nums[left],nums[right] = nums[right],nums[left]
            left +=1
            right -=1
class Solution:
    def buildTree(self, preorder: List[int], inorder: List[int]) -> TreeNode:
        # 改成普通局部变量，不挂self
        inorder_map = {val: idx for idx, val in enumerate(inorder)}
        
        def build(pre_left, pre_right, in_left, in_right):
            if pre_left > pre_right:
                return None
            
            root_val = preorder[pre_left]
            root = TreeNode(root_val)
            # 直接访问外层的局部变量，一样能用
            root_idx = inorder_map[root_val]
            left_size = root_idx - in_left
            
            root.left = build(pre_left+1, pre_left+left_size, in_left, root_idx-1)
            root.right = build(pre_left+left_size+1, pre_right, root_idx+1, in_right)
            return root
        
        return build(0, len(preorder)-1, 0, len(inorder)-1)
from typing import List
# Definition for a binary tree node.
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right
class Solution:
    def buildTree(self, preorder: List[int], inorder: List[int]) -> TreeNode:
        # 预构建中序遍历的值->下标映射，快速查找根节点位置
        self.inorder_map = {val: idx for idx, val in enumerate(inorder)}
        self.preorder = preorder
        
        # 递归函数：参数为 当前子树在先序的左右边界、在中序的左右边界
        def build(pre_left, pre_right, in_left, in_right):
            # 递归终止：左边界超过右边界，对应空节点
            if pre_left > pre_right:
                return None
            
            # 1. 先序区间的第一个元素就是当前根节点
            root_val = self.preorder[pre_left]
            root = TreeNode(root_val)
            
            # 2. 查到根节点在中序里的下标
            root_idx = self.inorder_map[root_val]
            
            # 3. 计算左子树的节点总数
            left_size = root_idx - in_left
            
            # 4. 递归构造左子树
            root.left = build(
                pre_left + 1, pre_left + left_size,
                in_left, root_idx - 1
            )
            
            # 5. 递归构造右子树
            root.right = build(
                pre_left + left_size + 1, pre_right,
                root_idx + 1, in_right
            )
            
            return root
        
        # 从完整数组区间启动递归
        return build(0, len(preorder)-1, 0, len(inorder)-1)