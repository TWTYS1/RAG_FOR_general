# React 学习笔记

## 什么是 React 组件？

React 组件本质上就是一个返回 JSX 的 JavaScript 函数。组件是 React 应用的核心构建块。

```jsx
function Welcome(props) {
  return <h1>Hello, {props.name}</h1>;
}
```

## 组件的特性

React 组件具有以下核心特性：

- **可复用性**：组件可以在不同地方重复使用
- **组合性**：组件可以嵌套组合，构建复杂 UI
- **状态管理**：通过 useState Hook 管理组件内部状态
- **副作用处理**：通过 useEffect Hook 处理数据获取、订阅等副作用

## 函数组件 vs 类组件

现代 React 推荐使用函数组件 + Hooks，取代传统的类组件。函数组件更简洁，更容易理解和测试。

## Props 和 State

- Props 是从父组件传递给子组件的只读数据
- State 是组件内部的可变数据，通过 useState 管理
- 单向数据流是 React 的核心设计原则
