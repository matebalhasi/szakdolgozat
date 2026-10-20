-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 20, 2026 at 09:08 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `manufacturing_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `assigned_operators`
--

CREATE TABLE `assigned_operators` (
  `machine_id` int(11) NOT NULL,
  `operator_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `assigned_operators`
--

INSERT INTO `assigned_operators` (`machine_id`, `operator_id`) VALUES
(1, 1),
(1, 2),
(2, 3),
(2, 4),
(3, 5),
(4, 1),
(4, 6),
(5, 2),
(5, 3),
(6, 4),
(6, 5),
(7, 6);

-- --------------------------------------------------------

--
-- Table structure for table `forms`
--

CREATE TABLE `forms` (
  `form_id` int(11) NOT NULL,
  `operator_id` int(11) NOT NULL,
  `machine_id` int(11) NOT NULL,
  `product_id` int(11) NOT NULL,
  `stationary_time` time DEFAULT NULL,
  `production_time` time NOT NULL,
  `product_amount` int(11) NOT NULL,
  `waste_amount` int(11) NOT NULL DEFAULT 0,
  `timestamp` datetime NOT NULL DEFAULT current_timestamp()
) ;

--
-- Dumping data for table `forms`
--

INSERT INTO `forms` (`form_id`, `operator_id`, `machine_id`, `product_id`, `stationary_time`, `production_time`, `product_amount`, `waste_amount`, `timestamp`) VALUES
(1, 1, 1, 1, '00:10:00', '04:00:00', 45, 2, '2026-09-01 08:00:00'),
(2, 2, 1, 1, '00:15:00', '04:00:00', 43, 1, '2026-09-01 13:00:00'),
(3, 3, 2, 2, '00:20:00', '05:00:00', 34, 2, '2026-09-01 08:00:00'),
(4, 4, 2, 2, '00:10:00', '05:00:00', 36, 1, '2026-09-01 13:00:00'),
(5, 5, 3, 3, '00:15:00', '06:00:00', 28, 2, '2026-09-01 08:00:00'),
(6, 1, 4, 4, '00:10:00', '04:00:00', 38, 1, '2026-09-01 08:00:00'),
(7, 6, 5, 5, '00:20:00', '05:00:00', 27, 2, '2026-09-01 08:00:00'),
(8, 1, 1, 1, '00:10:00', '04:00:00', 47, 1, '2026-09-02 08:00:00'),
(9, 2, 1, 1, '00:15:00', '04:00:00', 44, 2, '2026-09-02 13:00:00'),
(10, 3, 2, 2, '00:20:00', '05:00:00', 35, 1, '2026-09-02 08:00:00'),
(11, 4, 2, 2, '00:10:00', '05:00:00', 37, 1, '2026-09-02 13:00:00'),
(12, 5, 3, 3, '00:15:00', '06:00:00', 29, 2, '2026-09-02 08:00:00'),
(13, 1, 4, 4, '00:10:00', '04:00:00', 40, 1, '2026-09-02 08:00:00'),
(14, 6, 5, 5, '00:20:00', '05:00:00', 28, 2, '2026-09-02 08:00:00'),
(15, 1, 1, 1, '00:10:00', '04:00:00', 46, 2, '2026-09-03 08:00:00'),
(16, 2, 1, 1, '00:15:00', '04:00:00', 42, 1, '2026-09-03 13:00:00'),
(17, 3, 2, 2, '00:20:00', '05:00:00', 33, 2, '2026-09-03 08:00:00'),
(18, 4, 2, 2, '00:10:00', '05:00:00', 35, 1, '2026-09-03 13:00:00'),
(19, 5, 3, 3, '00:15:00', '06:00:00', 27, 2, '2026-09-03 08:00:00'),
(20, 1, 4, 4, '00:10:00', '04:00:00', 39, 1, '2026-09-03 08:00:00'),
(21, 6, 5, 5, '00:20:00', '05:00:00', 26, 1, '2026-09-03 08:00:00'),
(22, 1, 1, 1, '00:10:00', '04:00:00', 48, 1, '2026-09-04 08:00:00'),
(23, 2, 1, 1, '00:15:00', '04:00:00', 45, 2, '2026-09-04 13:00:00'),
(24, 3, 2, 2, '00:20:00', '05:00:00', 36, 1, '2026-09-04 08:00:00'),
(25, 4, 2, 2, '00:10:00', '05:00:00', 38, 1, '2026-09-04 13:00:00'),
(26, 5, 3, 3, '00:15:00', '06:00:00', 30, 2, '2026-09-04 08:00:00'),
(27, 1, 4, 4, '00:10:00', '04:00:00', 41, 1, '2026-09-04 08:00:00'),
(28, 6, 5, 5, '00:20:00', '05:00:00', 29, 2, '2026-09-04 08:00:00'),
(29, 1, 1, 1, '00:10:00', '04:00:00', 44, 2, '2026-09-05 08:00:00'),
(30, 2, 1, 1, '00:15:00', '04:00:00', 46, 1, '2026-09-05 13:00:00'),
(31, 3, 2, 2, '00:20:00', '05:00:00', 34, 2, '2026-09-05 08:00:00'),
(32, 4, 2, 2, '00:10:00', '05:00:00', 36, 1, '2026-09-05 13:00:00'),
(33, 5, 3, 3, '00:15:00', '06:00:00', 28, 2, '2026-09-05 08:00:00'),
(34, 1, 4, 4, '00:10:00', '04:00:00', 38, 1, '2026-09-05 08:00:00'),
(35, 6, 5, 5, '00:20:00', '05:00:00', 27, 2, '2026-09-05 08:00:00'),
(36, 1, 1, 1, '00:10:00', '04:00:00', 45, 1, '2026-09-06 08:00:00'),
(37, 2, 1, 1, '00:15:00', '04:00:00', 43, 2, '2026-09-06 13:00:00'),
(38, 3, 2, 2, '00:20:00', '05:00:00', 35, 1, '2026-09-06 08:00:00'),
(39, 4, 2, 2, '00:10:00', '05:00:00', 37, 1, '2026-09-06 13:00:00'),
(40, 5, 3, 3, '00:15:00', '06:00:00', 29, 2, '2026-09-06 08:00:00'),
(41, 1, 4, 4, '00:10:00', '04:00:00', 40, 1, '2026-09-06 08:00:00'),
(42, 6, 5, 5, '00:20:00', '05:00:00', 28, 2, '2026-09-06 08:00:00'),
(43, 1, 1, 1, '00:10:00', '04:00:00', 46, 1, '2026-09-07 08:00:00'),
(44, 2, 1, 1, '00:15:00', '04:00:00', 44, 1, '2026-09-07 13:00:00'),
(45, 3, 2, 2, '00:20:00', '05:00:00', 36, 2, '2026-09-07 08:00:00'),
(46, 4, 2, 2, '00:10:00', '05:00:00', 38, 1, '2026-09-07 13:00:00'),
(47, 5, 3, 3, '00:15:00', '06:00:00', 30, 2, '2026-09-07 08:00:00'),
(48, 1, 4, 4, '00:10:00', '04:00:00', 39, 1, '2026-09-07 08:00:00'),
(49, 6, 5, 5, '00:20:00', '05:00:00', 29, 2, '2026-09-07 08:00:00'),
(50, 1, 1, 1, '00:05:00', '04:00:00', 120, 0, '2026-09-07 14:00:00'),
(51, 5, 3, 3, '02:00:00', '06:00:00', 5, 1, '2026-09-07 14:00:00'),
(52, 3, 2, 2, '00:20:00', '05:00:00', 35, 50, '2026-09-06 14:00:00');

-- --------------------------------------------------------

--
-- Table structure for table `machine`
--

CREATE TABLE `machine` (
  `machine_id` int(11) NOT NULL,
  `machine_type_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `machine`
--

INSERT INTO `machine` (`machine_id`, `machine_type_id`) VALUES
(1, 1),
(2, 1),
(3, 1),
(4, 2),
(5, 2),
(6, 3),
(7, 3);

-- --------------------------------------------------------

--
-- Table structure for table `machine_type`
--

CREATE TABLE `machine_type` (
  `machine_type_id` int(11) NOT NULL,
  `brief_description` varchar(255) NOT NULL,
  `number_of_machines` int(11) NOT NULL DEFAULT 0
) ;

--
-- Dumping data for table `machine_type`
--

INSERT INTO `machine_type` (`machine_type_id`, `brief_description`, `number_of_machines`) VALUES
(1, 'CNC Milling Machine', 3),
(2, 'CNC Turning Machine', 2),
(3, 'Hydraulic Press', 2);

-- --------------------------------------------------------

--
-- Table structure for table `operator`
--

CREATE TABLE `operator` (
  `operator_id` int(11) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `b_date` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `operator`
--

INSERT INTO `operator` (`operator_id`, `name`, `b_date`) VALUES
(1, 'John Smith', '1985-04-12'),
(2, 'Maria Garcia', '1990-08-25'),
(3, 'David Brown', '1982-11-03'),
(4, 'Anna Wilson', '1995-02-17'),
(5, 'Michael Taylor', '1988-06-30'),
(6, 'Sarah Johnson', '1992-09-14');

-- --------------------------------------------------------

--
-- Table structure for table `orders`
--

CREATE TABLE `orders` (
  `order_id` int(11) NOT NULL,
  `due_date` date NOT NULL,
  `priority` int(11) NOT NULL DEFAULT 0
) ;

--
-- Dumping data for table `orders`
--

INSERT INTO `orders` (`order_id`, `due_date`, `priority`) VALUES
(1, '2026-09-08', 1),
(2, '2026-09-10', 2),
(3, '2026-09-12', 1),
(4, '2026-09-15', 3);

-- --------------------------------------------------------

--
-- Table structure for table `order_product`
--

CREATE TABLE `order_product` (
  `order_id` int(11) NOT NULL,
  `product_id` int(11) NOT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1
) ;

--
-- Dumping data for table `order_product`
--

INSERT INTO `order_product` (`order_id`, `product_id`, `quantity`) VALUES
(1, 1, 100),
(1, 2, 80),
(2, 3, 60),
(2, 4, 120),
(3, 2, 150),
(3, 5, 70),
(4, 1, 200),
(4, 4, 100);

-- --------------------------------------------------------

--
-- Table structure for table `product`
--

CREATE TABLE `product` (
  `product_id` int(11) NOT NULL,
  `manufacturing_time` time NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `product`
--

INSERT INTO `product` (`product_id`, `manufacturing_time`) VALUES
(1, '00:05:00'),
(2, '00:08:00'),
(3, '00:12:00'),
(4, '00:06:00'),
(5, '00:10:00');

-- --------------------------------------------------------

--
-- Table structure for table `production_plan`
--

CREATE TABLE `production_plan` (
  `plan_id` int(11) NOT NULL,
  `order_id` int(11) NOT NULL,
  `product_id` int(11) NOT NULL,
  `deadline` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `production_plan`
--

INSERT INTO `production_plan` (`plan_id`, `order_id`, `product_id`, `deadline`) VALUES
(1, 1, 1, '2026-09-08'),
(2, 1, 2, '2026-09-08'),
(3, 2, 3, '2026-09-10'),
(4, 2, 4, '2026-09-10'),
(5, 3, 2, '2026-09-12'),
(6, 3, 5, '2026-09-12'),
(7, 4, 1, '2026-09-15'),
(8, 4, 4, '2026-09-15');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `assigned_operators`
--
ALTER TABLE `assigned_operators`
  ADD PRIMARY KEY (`machine_id`,`operator_id`),
  ADD KEY `operator_id` (`operator_id`);

--
-- Indexes for table `forms`
--
ALTER TABLE `forms`
  ADD PRIMARY KEY (`form_id`),
  ADD KEY `operator_id` (`operator_id`),
  ADD KEY `machine_id` (`machine_id`),
  ADD KEY `product_id` (`product_id`);

--
-- Indexes for table `machine`
--
ALTER TABLE `machine`
  ADD PRIMARY KEY (`machine_id`),
  ADD KEY `machine_type_id` (`machine_type_id`);

--
-- Indexes for table `machine_type`
--
ALTER TABLE `machine_type`
  ADD PRIMARY KEY (`machine_type_id`);

--
-- Indexes for table `operator`
--
ALTER TABLE `operator`
  ADD PRIMARY KEY (`operator_id`);

--
-- Indexes for table `orders`
--
ALTER TABLE `orders`
  ADD PRIMARY KEY (`order_id`);

--
-- Indexes for table `order_product`
--
ALTER TABLE `order_product`
  ADD PRIMARY KEY (`order_id`,`product_id`),
  ADD KEY `product_id` (`product_id`);

--
-- Indexes for table `product`
--
ALTER TABLE `product`
  ADD PRIMARY KEY (`product_id`);

--
-- Indexes for table `production_plan`
--
ALTER TABLE `production_plan`
  ADD PRIMARY KEY (`plan_id`),
  ADD KEY `order_id` (`order_id`),
  ADD KEY `product_id` (`product_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `forms`
--
ALTER TABLE `forms`
  MODIFY `form_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `machine`
--
ALTER TABLE `machine`
  MODIFY `machine_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `machine_type`
--
ALTER TABLE `machine_type`
  MODIFY `machine_type_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `operator`
--
ALTER TABLE `operator`
  MODIFY `operator_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `orders`
--
ALTER TABLE `orders`
  MODIFY `order_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `product`
--
ALTER TABLE `product`
  MODIFY `product_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `production_plan`
--
ALTER TABLE `production_plan`
  MODIFY `plan_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `assigned_operators`
--
ALTER TABLE `assigned_operators`
  ADD CONSTRAINT `assigned_operators_ibfk_1` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`machine_id`),
  ADD CONSTRAINT `assigned_operators_ibfk_2` FOREIGN KEY (`operator_id`) REFERENCES `operator` (`operator_id`);

--
-- Constraints for table `forms`
--
ALTER TABLE `forms`
  ADD CONSTRAINT `forms_ibfk_1` FOREIGN KEY (`operator_id`) REFERENCES `operator` (`operator_id`),
  ADD CONSTRAINT `forms_ibfk_2` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`machine_id`),
  ADD CONSTRAINT `forms_ibfk_3` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`);

--
-- Constraints for table `machine`
--
ALTER TABLE `machine`
  ADD CONSTRAINT `machine_ibfk_1` FOREIGN KEY (`machine_type_id`) REFERENCES `machine_type` (`machine_type_id`);

--
-- Constraints for table `order_product`
--
ALTER TABLE `order_product`
  ADD CONSTRAINT `order_product_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`),
  ADD CONSTRAINT `order_product_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`);

--
-- Constraints for table `production_plan`
--
ALTER TABLE `production_plan`
  ADD CONSTRAINT `production_plan_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`),
  ADD CONSTRAINT `production_plan_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
