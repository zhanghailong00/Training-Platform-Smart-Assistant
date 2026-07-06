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
        
            